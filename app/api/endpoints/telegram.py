from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.schemas import PreviewAdminItem, PreviewAdminListResponse, PreviewResponse, TelegramWebhookPayload
from app.services.image_service import ImageService
from app.services.google_tasks_service import build_google_tasks_service
from app.services.processing_state_service import (
    is_duplicate_image,
    record_log,
    record_processed_image,
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
    format_preview_message,
    parse_edit_command,
    parse_preview_callback,
)
from app.services.vision_service import build_vision_service, parse_vision_payload

router = APIRouter()


async def _finalize_response(db: Session, response: PreviewResponse) -> PreviewResponse:
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
        response.telegram_api_results = await build_telegram_bot_service().execute_api_calls(
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
    x_telegram_bot_api_secret_token: str = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Receive a Telegram webhook, download photos, detect duplicates and build a preview.
    """
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Secret Token")

    raw_payload = await request.json()
    update = TelegramWebhookPayload.model_validate(raw_payload)
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

    edit_command = parse_edit_command(extract_message_text(update.message))
    if edit_command is not None:
        preview_id, corrected_lines = edit_command
        chat_id = extract_chat_id(update.message)
        preview = get_pending_preview(db, preview_id)
        if preview is None:
            record_log(
                db,
                status="edit_missing_preview",
                error_message=f"Preview {preview_id} was not found.",
            )
            return await _finalize_response(db, PreviewResponse(
                status="not_found",
                preview_id=preview_id,
                action="edit_submit",
                message="Preview not found.",
                telegram_api_calls=(
                    [build_send_message_call(chat_id, "Preview not found.")]
                    if chat_id is not None
                    else []
                ),
            ))

        if preview.status not in {"editing", "pending"}:
            return await _finalize_response(db, PreviewResponse(
                status="ignored",
                preview_id=preview_id,
                action="edit_submit",
                message=f"Preview is already {preview.status}.",
                telegram_api_calls=(
                    [build_send_message_call(chat_id, f"Preview is already {preview.status}.")]
                    if chat_id is not None
                    else []
                ),
            ))

        edited_tasks = build_preview_from_lines(corrected_lines)
        if not edited_tasks:
            return await _finalize_response(db, PreviewResponse(
                status="invalid",
                preview_id=preview_id,
                action="edit_submit",
                message="No valid task lines were provided in the edit.",
                telegram_api_calls=(
                    [build_send_message_call(chat_id, "No valid task lines were provided in the edit.")]
                    if chat_id is not None
                    else []
                ),
            ))

        replace_preview_tasks(
            db,
            preview=preview,
            tasks=edited_tasks,
            source="manual_edit",
            status="pending",
        )
        record_log(db, status="preview_edited", tasks_detected=len(edited_tasks))
        edited_message = "Preview updated with your edits."
        return await _finalize_response(db, PreviewResponse(
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
        ))

    if update.callback_query:
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
            return await _finalize_response(db, PreviewResponse(
                status="ignored",
                action="unknown",
                message="Unsupported callback action.",
                telegram_api_calls=(
                    [build_answer_callback_call(callback_query_id, "Unsupported action.")]
                    if isinstance(callback_query_id, str)
                    else []
                ),
            ))

        action, preview_id = callback
        preview = get_pending_preview(db, preview_id)
        if preview is None:
            record_log(
                db,
                status="callback_missing_preview",
                error_message=f"Preview {preview_id} was not found.",
            )
            return await _finalize_response(db, PreviewResponse(
                status="not_found",
                preview_id=preview_id,
                action=action,
                message="Preview not found or already expired.",
                telegram_api_calls=(
                    [build_answer_callback_call(callback_query_id, "Preview not found.")]
                    if isinstance(callback_query_id, str)
                    else []
                ),
            ))

        tasks = load_preview_tasks(preview)
        if action == "confirm":
            if preview.status == "completed":
                ignored_message = f"Preview is already {preview.status}."
                return await _finalize_response(db, PreviewResponse(
                    status="ignored",
                    preview_id=preview_id,
                    action=action,
                    tasks=tasks,
                    message=ignored_message,
                    telegram_api_calls=(
                        [build_answer_callback_call(callback_query_id, ignored_message)]
                        if isinstance(callback_query_id, str)
                        else []
                    ),
                ))
            if preview.status not in {"pending", "editing", "confirmed", "creation_failed"}:
                ignored_message = f"Preview is already {preview.status}."
                return await _finalize_response(db, PreviewResponse(
                    status="ignored",
                    preview_id=preview_id,
                    action=action,
                    tasks=tasks,
                    message=ignored_message,
                    telegram_api_calls=(
                        [build_answer_callback_call(callback_query_id, ignored_message)]
                        if isinstance(callback_query_id, str)
                        else []
                    ),
                ))

            update_preview_status(db, preview=preview, status="confirmed")
            try:
                result = await execute_preview_tasks(
                    db,
                    preview_id=preview_id,
                    tasks=tasks,
                    google_tasks_service=build_google_tasks_service(),
                )
            except Exception as exc:
                update_preview_status(db, preview=preview, status="creation_failed")
                record_log(
                    db,
                    status="google_tasks_failed",
                    tasks_detected=len(tasks),
                    error_message=str(exc),
                )
                return await _finalize_response(db, PreviewResponse(
                    status="creation_failed",
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
                ))

            update_preview_status(db, preview=preview, status="completed")
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
            return await _finalize_response(db, PreviewResponse(
                status="completed",
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
            ))

        if action == "edit":
            update_preview_status(db, preview=preview, status="editing")
            record_log(db, status="preview_edit_requested", tasks_detected=len(tasks))
            edit_message = (
                f"Edit requested for preview {preview_id}.\n"
                f"Reply with /edit {preview_id} followed by the corrected task lines."
            )
            return await _finalize_response(db, PreviewResponse(
                status="editing",
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
            ))

        update_preview_status(db, preview=preview, status="cancelled")
        record_log(db, status="preview_cancelled", tasks_detected=len(tasks))
        cancelled_message = "Preview cancelled. Nothing was created."
        return await _finalize_response(db, PreviewResponse(
            status="cancelled",
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
        ))

    candidate_lines = update.mock_lines or extract_caption_lines(update.message)
    chat_id = extract_chat_id(update.message)

    image_hash: str | None = None
    processed_bytes: bytes | None = None
    if update.message:
        file_id = extract_photo_file_id(update.message)
        if file_id:
            try:
                telegram_bot = build_telegram_bot_service()
                file_path = await telegram_bot.get_file_path(file_id)
                image_bytes = await telegram_bot.download_file_bytes(file_path)
                processed_bytes = ImageService.preprocess_image(image_bytes)
                image_hash = ImageService.calculate_hash(processed_bytes)
            except Exception as exc:
                record_log(
                    db,
                    status="image_download_failed",
                    error_message=str(exc),
                )
                raise HTTPException(
                    status_code=502,
                    detail="Failed to download or preprocess the Telegram image.",
                ) from exc

            if is_duplicate_image(db, image_hash):
                record_log(db, status="duplicate_image")
                return await _finalize_response(db, PreviewResponse(
                    status="duplicate",
                    duplicate=True,
                    image_hash=image_hash,
                    message="Duplicate image detected. Nothing was created.",
                ))

            record_processed_image(db, image_hash)
            record_log(db, status="image_received")

    tasks = []
    used_vision = False
    if processed_bytes:
        try:
            vision_service = build_vision_service(settings.VISION_API_URL)
            vision_payload = await vision_service.extract_tasks(processed_bytes)
            tasks, global_confidence = parse_vision_payload(vision_payload)
            if tasks and global_confidence >= 0.3:
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

    if not tasks:
        tasks = build_preview_from_lines(candidate_lines)

    preview_message = format_preview_message(tasks) if tasks else "Webhook received. Image stored for processing."
    if not used_vision and tasks:
        preview_message = f"{preview_message}\nSource: fallback text parsing."
    record_log(db, status="preview_ready", tasks_detected=len(tasks))

    preview_id: int | None = None
    reply_markup = None
    if tasks:
        source = "vision" if used_vision else "fallback_text"
        pending_preview = create_pending_preview(
            db,
            tasks=tasks,
            image_hash=image_hash,
            source=source,
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
        image_hash=image_hash,
        preview_id=preview_id,
        message=preview_message,
        reply_markup=reply_markup,
        telegram_api_calls=telegram_api_calls,
    ))
