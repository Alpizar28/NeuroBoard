"""Telegram webhook endpoint.

Handles three distinct flows dispatched from a single POST /webhook:
  1. /edit command   — manual line correction of a pending preview
  2. callback_query  — inline keyboard actions (confirm / edit / cancel)
  3. incoming media  — image or voice/audio message → Vision / Whisper → preview
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import (
    PREVIEW_ACTIVE_STATUSES,
    PREVIEW_STATUS_CANCELLED,
    PREVIEW_STATUS_COMPLETED,
    PREVIEW_STATUS_CONFIRMED,
    PREVIEW_STATUS_CREATION_FAILED,
    PREVIEW_STATUS_EDITING,
    PREVIEW_STATUS_PENDING,
)
from app.db.database import get_db
from app.models.schemas import (
    PreviewAdminItem,
    PreviewAdminListResponse,
    PreviewResponse,
    TelegramWebhookPayload,
    TelegramWebhookTestPayload,
)
from app.services.audio_service import AudioService
from app.services.google_tasks_service import build_google_tasks_service
from app.services.image_service import ImageService
from app.services.processing_state_service import (
    is_duplicate_media,
    record_log,
    record_processed_media,
)
from app.services.preview_state_service import (
    create_pending_preview,
    expire_stale_previews,
    get_pending_preview,
    list_previews,
    load_preview_tasks,
    replace_preview_tasks,
    update_preview_status,
)
from app.services.task_parsing_service import build_preview_from_lines
from app.services.task_execution_service import execute_preview_tasks
from app.services.telegram_service import (
    build_answer_callback_call,
    build_edit_message_call,
    build_send_message_call,
    build_telegram_bot_service,
    build_preview_reply_markup,
    extract_chat_id,
    extract_caption_lines,
    extract_message_text,
    extract_message_id,
    extract_photo_file_id,
    extract_voice_file_id,
    format_preview_message,
    parse_edit_command,
    parse_preview_callback,
)
from app.services.vision_service import build_vision_service, parse_vision_payload

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _finalize_response(db: Session, response: PreviewResponse) -> PreviewResponse:
    """Dispatch pending Telegram API calls and attach results to the response."""
    if not response.telegram_api_calls:
        return response

    if not settings.TELEGRAM_BOT_TOKEN:
        record_log(
            db,
            status="telegram_dispatch_skipped",
            error_message="TELEGRAM_BOT_TOKEN is not configured.",
        )
        response.telegram_api_results = [
            {"ok": False, "error": "TELEGRAM_BOT_TOKEN is not configured."}
        ]
        return response

    try:
        telegram_bot = build_telegram_bot_service()
        response.telegram_api_results = await telegram_bot.execute_api_calls(
            response.telegram_api_calls
        )
    except Exception as exc:
        record_log(
            db,
            status="telegram_dispatch_failed",
            error_message=str(exc),
        )
        response.telegram_api_results = [{"ok": False, "error": str(exc)}]
    return response


def _run_expire_stale_previews(db: Session) -> None:
    """Background task: expire stale previews without blocking the webhook response."""
    expired_count = expire_stale_previews(
        db,
        max_age_minutes=settings.PREVIEW_EXPIRATION_MINUTES,
    )
    if expired_count:
        record_log(
            db,
            status="previews_expired",
            error_message=f"Expired {expired_count} stale preview(s).",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Flow handlers
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_edit_command(
    update: TelegramWebhookPayload,
    db: Session,
) -> PreviewResponse | None:
    """Handle the /edit <preview_id> text command.

    Returns a PreviewResponse if the update contained an edit command,
    or None if it didn't.
    """
    edit_command = parse_edit_command(extract_message_text(update.message))
    if edit_command is None:
        return None

    preview_id, corrected_lines = edit_command
    chat_id = extract_chat_id(update.message)
    preview = get_pending_preview(db, preview_id)

    if preview is None:
        record_log(
            db,
            status="edit_missing_preview",
            error_message=f"Preview {preview_id} was not found.",
        )
        return PreviewResponse(
            status="not_found",
            preview_id=preview_id,
            action="edit_submit",
            message="Preview not found.",
            telegram_api_calls=(
                [build_send_message_call(chat_id, "Preview not found.")]
                if chat_id is not None
                else []
            ),
        )

    if preview.status not in {PREVIEW_STATUS_EDITING, PREVIEW_STATUS_PENDING}:
        msg = f"Preview is already {preview.status}."
        return PreviewResponse(
            status="ignored",
            preview_id=preview_id,
            action="edit_submit",
            message=msg,
            telegram_api_calls=(
                [build_send_message_call(chat_id, msg)]
                if chat_id is not None
                else []
            ),
        )

    edited_tasks = build_preview_from_lines(corrected_lines)
    if not edited_tasks:
        return PreviewResponse(
            status="invalid",
            preview_id=preview_id,
            action="edit_submit",
            message="No valid task lines were provided in the edit.",
            telegram_api_calls=(
                [build_send_message_call(chat_id, "No valid task lines were provided in the edit.")]
                if chat_id is not None
                else []
            ),
        )

    replace_preview_tasks(
        db,
        preview=preview,
        tasks=edited_tasks,
        source="manual_edit",
        status=PREVIEW_STATUS_PENDING,
    )
    record_log(db, status="preview_edited", tasks_detected=len(edited_tasks))
    edited_message = "Preview updated with your edits."
    return PreviewResponse(
        status="edited",
        preview_id=preview_id,
        action="edit_submit",
        tasks=edited_tasks,
        image_hash=preview.image_hash,
        message=edited_message,
        reply_markup=build_preview_reply_markup(preview_id),
        telegram_api_calls=(
            [
                build_send_message_call(
                    chat_id,
                    edited_message,
                    reply_markup=build_preview_reply_markup(preview_id),
                )
            ]
            if chat_id is not None
            else []
        ),
    )


async def _handle_callback_query(
    update: TelegramWebhookPayload,
    db: Session,
) -> PreviewResponse | None:
    """Handle inline keyboard callback_query actions (confirm / edit / cancel).

    Returns a PreviewResponse if the update contained a callback_query,
    or None if it didn't.
    """
    if not update.callback_query:
        return None

    callback_query = update.callback_query
    callback = parse_preview_callback(update.callback_query.get("data"))
    callback_query_id = callback_query.get("id")
    callback_message = callback_query.get("message") or {}
    callback_chat_id = extract_chat_id(callback_message)
    callback_message_id = extract_message_id(callback_message)

    if callback is None:
        record_log(
            db,
            status="callback_invalid",
            error_message="Unsupported callback payload.",
        )
        return PreviewResponse(
            status="ignored",
            action="unknown",
            message="Unsupported callback action.",
            telegram_api_calls=(
                [build_answer_callback_call(callback_query_id, "Unsupported action.")]
                if isinstance(callback_query_id, str)
                else []
            ),
        )

    action, preview_id = callback
    preview = get_pending_preview(db, preview_id)

    if preview is None:
        record_log(
            db,
            status="callback_missing_preview",
            error_message=f"Preview {preview_id} was not found.",
        )
        return PreviewResponse(
            status="not_found",
            preview_id=preview_id,
            action=action,
            message="Preview not found or already expired.",
            telegram_api_calls=(
                [build_answer_callback_call(callback_query_id, "Preview not found.")]
                if isinstance(callback_query_id, str)
                else []
            ),
        )

    tasks = load_preview_tasks(preview)

    # ── confirm ──────────────────────────────────────────────────────────────
    if action == "confirm":
        if preview.status == PREVIEW_STATUS_COMPLETED:
            msg = f"Preview is already {preview.status}."
            return PreviewResponse(
                status="ignored",
                preview_id=preview_id,
                action=action,
                tasks=tasks,
                message=msg,
                telegram_api_calls=(
                    [build_answer_callback_call(callback_query_id, msg)]
                    if isinstance(callback_query_id, str)
                    else []
                ),
            )

        if preview.status not in {
            PREVIEW_STATUS_PENDING,
            PREVIEW_STATUS_EDITING,
            PREVIEW_STATUS_CONFIRMED,
            PREVIEW_STATUS_CREATION_FAILED,
        }:
            msg = f"Preview is already {preview.status}."
            return PreviewResponse(
                status="ignored",
                preview_id=preview_id,
                action=action,
                tasks=tasks,
                message=msg,
                telegram_api_calls=(
                    [build_answer_callback_call(callback_query_id, msg)]
                    if isinstance(callback_query_id, str)
                    else []
                ),
            )

        update_preview_status(db, preview=preview, status=PREVIEW_STATUS_CONFIRMED)
        try:
            result = await execute_preview_tasks(
                db,
                preview_id=preview_id,
                tasks=tasks,
                google_tasks_service=build_google_tasks_service(db),
            )
        except Exception as exc:
            update_preview_status(db, preview=preview, status=PREVIEW_STATUS_CREATION_FAILED)
            record_log(
                db,
                status="google_tasks_failed",
                tasks_detected=len(tasks),
                error_message=str(exc),
            )
            return PreviewResponse(
                status=PREVIEW_STATUS_CREATION_FAILED,
                preview_id=preview_id,
                action=action,
                tasks=tasks,
                image_hash=preview.image_hash,
                message="Preview confirmed, but task creation failed. Retry confirm after fixing credentials or network.",
                telegram_api_calls=(
                    [
                        build_answer_callback_call(callback_query_id, "Task creation failed."),
                        build_edit_message_call(
                            callback_chat_id,
                            callback_message_id,
                            "Preview confirmed, but task creation failed. Retry confirm after fixing credentials or network.",
                            reply_markup=build_preview_reply_markup(preview_id),
                        ),
                    ]
                    if isinstance(callback_query_id, str)
                    and callback_chat_id is not None
                    and callback_message_id is not None
                    else []
                ),
            )

        update_preview_status(db, preview=preview, status=PREVIEW_STATUS_COMPLETED)
        record_log(
            db,
            status="google_tasks_created",
            tasks_detected=len(tasks),
            tasks_created=result.created_count,
        )
        completed_message = (
            f"Created {result.created_count} task(s). "
            f"Skipped {result.skipped_count} already-created task(s)."
        )
        return PreviewResponse(
            status=PREVIEW_STATUS_COMPLETED,
            preview_id=preview_id,
            action=action,
            tasks=tasks,
            image_hash=preview.image_hash,
            message=completed_message,
            telegram_api_calls=(
                [
                    build_answer_callback_call(callback_query_id, "Tasks created."),
                    build_edit_message_call(
                        callback_chat_id,
                        callback_message_id,
                        completed_message,
                    ),
                ]
                if isinstance(callback_query_id, str)
                and callback_chat_id is not None
                and callback_message_id is not None
                else []
            ),
        )

    # ── edit ─────────────────────────────────────────────────────────────────
    if action == "edit":
        update_preview_status(db, preview=preview, status=PREVIEW_STATUS_EDITING)
        record_log(db, status="preview_edit_requested", tasks_detected=len(tasks))
        edit_message = (
            f"Edit requested for preview {preview_id}.\n"
            f"Reply with /edit {preview_id} followed by the corrected task lines."
        )
        return PreviewResponse(
            status=PREVIEW_STATUS_EDITING,
            preview_id=preview_id,
            action=action,
            tasks=tasks,
            image_hash=preview.image_hash,
            message=edit_message,
            reply_markup=build_preview_reply_markup(preview_id),
            telegram_api_calls=(
                [
                    build_answer_callback_call(callback_query_id, "Send your corrected lines."),
                    build_edit_message_call(
                        callback_chat_id,
                        callback_message_id,
                        edit_message,
                        reply_markup=build_preview_reply_markup(preview_id),
                    ),
                ]
                if isinstance(callback_query_id, str)
                and callback_chat_id is not None
                and callback_message_id is not None
                else []
            ),
        )

    # ── cancel (default) ─────────────────────────────────────────────────────
    update_preview_status(db, preview=preview, status=PREVIEW_STATUS_CANCELLED)
    record_log(db, status="preview_cancelled", tasks_detected=len(tasks))
    cancelled_message = "Preview cancelled. Nothing was created."
    return PreviewResponse(
        status=PREVIEW_STATUS_CANCELLED,
        preview_id=preview_id,
        action=action,
        tasks=tasks,
        image_hash=preview.image_hash,
        message=cancelled_message,
        telegram_api_calls=(
            [
                build_answer_callback_call(callback_query_id, "Cancelled."),
                build_edit_message_call(
                    callback_chat_id,
                    callback_message_id,
                    cancelled_message,
                ),
            ]
            if isinstance(callback_query_id, str)
            and callback_chat_id is not None
            and callback_message_id is not None
            else []
        ),
    )


async def _handle_incoming_message(
    update: TelegramWebhookPayload,
    db: Session,
    candidate_lines: list[str] | None = None,
) -> PreviewResponse:
    """Handle an incoming image, voice message, or caption-only message.

    candidate_lines: pre-populated lines (from TelegramWebhookTestPayload.mock_lines
    in the test endpoint). If None, lines are extracted from the message caption.
    """
    chat_id = extract_chat_id(update.message)
    if candidate_lines is None:
        candidate_lines = extract_caption_lines(update.message)

    media_hash: str | None = None
    processed_image_bytes: bytes | None = None
    processed_audio_bytes: bytes | None = None
    media_source: str = "unknown"

    telegram_bot = build_telegram_bot_service() if settings.TELEGRAM_BOT_TOKEN else None

    # ── Image branch ──────────────────────────────────────────────────────────
    if update.message:
        file_id = extract_photo_file_id(update.message)
        if file_id and telegram_bot:
            try:
                file_path = await telegram_bot.get_file_path(file_id)
                image_bytes = await telegram_bot.download_file_bytes(file_path)
                processed_image_bytes = ImageService.preprocess_image(image_bytes)
                media_hash = ImageService.calculate_hash(processed_image_bytes)
            except Exception as exc:
                record_log(
                    db,
                    status="image_download_failed",
                    error_message=str(exc),
                )
                # Return 200 (not 502) so Telegram doesn't retry the webhook
                error_msg = "Could not download or process the image. Please try again."
                return await _finalize_response(db, PreviewResponse(
                    status="error",
                    message=error_msg,
                    telegram_api_calls=(
                        [build_send_message_call(chat_id, error_msg)]
                        if chat_id is not None
                        else []
                    ),
                ))

            if is_duplicate_media(db, media_hash):
                record_log(db, status="duplicate_image")
                dup_msg = "This image was already processed."
                return await _finalize_response(db, PreviewResponse(
                    status="duplicate",
                    duplicate=True,
                    image_hash=media_hash,
                    media_hash=media_hash,
                    message=dup_msg,
                    telegram_api_calls=(
                        [build_send_message_call(chat_id, dup_msg)]
                        if chat_id is not None
                        else []
                    ),
                ))

            record_processed_media(db, media_hash, media_type="image")
            record_log(db, status="image_received")
            media_source = "image"

        # ── Audio / Voice branch ─────────────────────────────────────────────
        voice_file_id = extract_voice_file_id(update.message)
        if voice_file_id and telegram_bot and not processed_image_bytes:
            try:
                file_path = await telegram_bot.get_file_path(voice_file_id)
                audio_bytes = await telegram_bot.download_file_bytes(file_path)
                audio_hash = AudioService.calculate_hash(audio_bytes)
            except Exception as exc:
                record_log(db, status="audio_download_failed", error_message=str(exc))
                error_msg = "Could not download the audio message. Please try again."
                return await _finalize_response(db, PreviewResponse(
                    status="error",
                    message=error_msg,
                    telegram_api_calls=(
                        [build_send_message_call(chat_id, error_msg)]
                        if chat_id is not None
                        else []
                    ),
                ))

            if is_duplicate_media(db, audio_hash):
                record_log(db, status="duplicate_audio")
                dup_msg = "This audio was already processed."
                return await _finalize_response(db, PreviewResponse(
                    status="duplicate",
                    duplicate=True,
                    media_hash=audio_hash,
                    message=dup_msg,
                    telegram_api_calls=(
                        [build_send_message_call(chat_id, dup_msg)]
                        if chat_id is not None
                        else []
                    ),
                ))

            # Preprocess and transcribe
            try:
                processing_msg = "Processing your audio... This may take a moment."
                if chat_id is not None and telegram_bot:
                    try:
                        await telegram_bot.execute_api_call(
                            build_send_message_call(chat_id, processing_msg)
                        )
                    except Exception:
                        pass  # Non-critical notification

                processed_audio_bytes = await AudioService.preprocess_audio(audio_bytes)
                transcribed_text = await AudioService.transcribe(processed_audio_bytes)
                if transcribed_text:
                    candidate_lines = [
                        line.strip()
                        for line in transcribed_text.splitlines()
                        if line.strip()
                    ]
                media_hash = audio_hash
                record_processed_media(db, audio_hash, media_type="audio")
                record_log(db, status="audio_received")
                media_source = "audio_whisper"
            except Exception as exc:
                record_log(db, status="audio_transcription_failed", error_message=str(exc))
                error_msg = "Could not transcribe the audio. Please try again or send the tasks as text."
                return await _finalize_response(db, PreviewResponse(
                    status="error",
                    message=error_msg,
                    telegram_api_calls=(
                        [build_send_message_call(chat_id, error_msg)]
                        if chat_id is not None
                        else []
                    ),
                ))

    # ── Vision API (images only) ──────────────────────────────────────────────
    tasks = []
    used_vision = False
    if processed_image_bytes:
        try:
            vision_service = build_vision_service(settings.VISION_API_URL)
            vision_payload = await vision_service.extract_tasks(processed_image_bytes)
            tasks, global_confidence = parse_vision_payload(vision_payload)
            if tasks and global_confidence >= settings.VISION_MIN_CONFIDENCE:
                used_vision = True
                record_log(
                    db,
                    status="vision_success",
                    tasks_detected=len(tasks),
                )
            else:
                tasks = []
                record_log(
                    db,
                    status="vision_low_confidence",
                    error_message="Vision returned no tasks or low confidence.",
                )
        except Exception as exc:
            record_log(
                db,
                status="vision_failed",
                error_message=str(exc),
            )

    # ── Fallback text parsing ─────────────────────────────────────────────────
    if not tasks:
        tasks = build_preview_from_lines(candidate_lines)

    # ── Build preview message ─────────────────────────────────────────────────
    if tasks:
        source_label = media_source if media_source != "unknown" else (
            "vision" if used_vision else "fallback_text"
        )
        if used_vision:
            source_label = "vision"
        elif processed_audio_bytes:
            source_label = "audio_whisper"
        else:
            source_label = "fallback_text"

        preview_message = format_preview_message(tasks)
        if not used_vision and not processed_audio_bytes:
            preview_message = f"{preview_message}\nSource: fallback text parsing."
    else:
        source_label = "unknown"
        preview_message = "Webhook received. No tasks detected."

    record_log(db, status="preview_ready", tasks_detected=len(tasks))

    preview_id: int | None = None
    reply_markup = None
    if tasks:
        pending_preview = create_pending_preview(
            db,
            tasks=tasks,
            image_hash=media_hash,
            source=source_label,
        )
        preview_id = pending_preview.id
        reply_markup = build_preview_reply_markup(preview_id)

    telegram_api_calls = (
        [build_send_message_call(chat_id, preview_message, reply_markup=reply_markup)]
        if chat_id is not None and preview_message
        else []
    )

    return await _finalize_response(db, PreviewResponse(
        status="ok",
        tasks=tasks,
        image_hash=media_hash,
        media_hash=media_hash,
        preview_id=preview_id,
        message=preview_message,
        reply_markup=reply_markup,
        telegram_api_calls=telegram_api_calls,
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/previews", response_model=PreviewAdminListResponse)
def list_pending_previews(
    status: str | None = Query(default=None),
    preview_id: int | None = Query(default=None, ge=1),
    image_hash: str | None = Query(default=None),
    updated_from: str | None = Query(default=None),
    updated_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    x_admin_api_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not settings.ADMIN_API_TOKEN or x_admin_api_token != settings.ADMIN_API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    def _parse_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid datetime filter: {value}",
            ) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    parsed_updated_from = _parse_datetime(updated_from)
    parsed_updated_to = _parse_datetime(updated_to)

    previews = list_previews(
        db,
        status=status,
        preview_id=preview_id,
        image_hash=image_hash,
        updated_from=parsed_updated_from,
        updated_to=parsed_updated_to,
        limit=limit,
    )
    items = [
        PreviewAdminItem(
            id=preview.id,
            status=preview.status,
            source=preview.source,
            image_hash=preview.image_hash,
            media_hash=preview.image_hash,
            task_count=len(load_preview_tasks(preview)),
            created_at=preview.created_at.isoformat(),
            updated_at=preview.updated_at.isoformat(),
        )
        for preview in previews
    ]
    return PreviewAdminListResponse(
        items=items,
        total=len(items),
        status_filter=status,
        preview_id_filter=preview_id,
        image_hash_filter=image_hash,
        updated_from_filter=parsed_updated_from.isoformat() if parsed_updated_from else None,
        updated_to_filter=parsed_updated_to.isoformat() if parsed_updated_to else None,
    )


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Receive a Telegram webhook update and dispatch to the appropriate handler."""
    if not settings.TELEGRAM_SECRET_TOKEN or x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Secret Token")

    raw_payload = await request.json()
    update = TelegramWebhookPayload.model_validate(raw_payload)

    # Expire stale previews in the background — non-blocking
    background_tasks.add_task(_run_expire_stale_previews, db)

    # Dispatch to the appropriate handler
    if (response := await _handle_edit_command(update, db)) is not None:
        return response

    if (response := await _handle_callback_query(update, db)) is not None:
        return response

    return await _handle_incoming_message(update, db)


@router.post("/webhook/test")
async def telegram_webhook_test(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Test-only webhook endpoint that accepts mock_lines to bypass image download.

    Only active when ENABLE_TEST_ENDPOINT=true in the environment.
    """
    if not settings.ENABLE_TEST_ENDPOINT:
        raise HTTPException(status_code=404, detail="Not found")

    if not settings.TELEGRAM_SECRET_TOKEN or x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Secret Token")

    raw_payload = await request.json()
    update = TelegramWebhookTestPayload.model_validate(raw_payload)

    background_tasks.add_task(_run_expire_stale_previews, db)

    if (response := await _handle_edit_command(update, db)) is not None:
        return response

    if (response := await _handle_callback_query(update, db)) is not None:
        return response

    # Pass mock_lines directly as candidate_lines, bypassing media download
    candidate_lines = update.mock_lines if update.mock_lines else None
    return await _handle_incoming_message(update, db, candidate_lines=candidate_lines)
