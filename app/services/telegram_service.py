from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx

from app.core.config import settings
from app.models.schemas import ParsedTask


def format_preview_message(tasks: list[ParsedTask]) -> str:
    if not tasks:
        return "No tasks detected."

    grouped: dict[str, list[ParsedTask]] = defaultdict(list)
    for task in tasks:
        grouped[task.list_name].append(task)

    sections: list[str] = ["Preview before confirmation:"]
    for list_name in sorted(grouped):
        sections.append(f"[{list_name}]")
        for task in grouped[list_name]:
            suffix = f" ({task.due_date.isoformat()})" if task.due_date else ""
            sections.append(f"- {task.text}{suffix}")
            for subtask in task.subtasks:
                sections.append(f"  * {subtask}")

    sections.append("Buttons: Confirm | Edit | Cancel")
    return "\n".join(sections)


def build_preview_reply_markup(preview_id: int) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Confirm",
                    "callback_data": f"preview:confirm:{preview_id}",
                },
                {
                    "text": "Edit",
                    "callback_data": f"preview:edit:{preview_id}",
                },
                {
                    "text": "Cancel",
                    "callback_data": f"preview:cancel:{preview_id}",
                },
            ]
        ]
    }


def build_send_message_call(
    chat_id: int,
    text: str,
    *,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "method": "sendMessage",
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return payload


def build_edit_message_call(
    chat_id: int,
    message_id: int,
    text: str,
    *,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "method": "editMessageText",
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return payload


def build_answer_callback_call(
    callback_query_id: str,
    text: str,
) -> dict[str, Any]:
    return {
        "method": "answerCallbackQuery",
        "callback_query_id": callback_query_id,
        "text": text,
    }


def extract_photo_file_id(message: dict[str, Any] | None) -> str | None:
    if not message:
        return None

    photos = message.get("photo") or []
    if not photos:
        return None

    largest = max(photos, key=lambda item: item.get("file_size") or 0)
    return largest.get("file_id")


def extract_caption_lines(message: dict[str, Any] | None) -> list[str]:
    if not message:
        return []

    caption = (message.get("caption") or "").strip()
    if not caption:
        return []

    return [line for line in caption.splitlines() if line.strip()]


def extract_message_text(message: dict[str, Any] | None) -> str:
    if not message:
        return ""
    return (message.get("text") or "").strip()


def extract_chat_id(message: dict[str, Any] | None) -> int | None:
    if not message:
        return None
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    return chat_id if isinstance(chat_id, int) else None


def extract_message_id(message: dict[str, Any] | None) -> int | None:
    if not message:
        return None
    message_id = message.get("message_id")
    return message_id if isinstance(message_id, int) else None


def parse_edit_command(message_text: str) -> tuple[int, list[str]] | None:
    if not message_text:
        return None

    lines = [line.rstrip() for line in message_text.splitlines()]
    if not lines:
        return None

    first_line = lines[0].strip()
    parts = first_line.split(maxsplit=1)
    if len(parts) != 2 or parts[0] not in {"/edit", "/edit_preview"}:
        return None

    try:
        preview_id = int(parts[1])
    except ValueError:
        return None

    corrected_lines = [line for line in lines[1:] if line.strip()]
    return preview_id, corrected_lines


class TelegramBotService:
    """Small wrapper around the Telegram Bot API for file downloads."""

    def __init__(
        self,
        bot_token: str,
        *,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.bot_token = bot_token
        self.timeout_seconds = timeout_seconds
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.file_base = f"https://api.telegram.org/file/bot{bot_token}"

    async def get_file_path(self, file_id: str) -> str:
        if not self.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.api_base}/getFile",
                params={"file_id": file_id},
            )
            response.raise_for_status()
            payload = response.json()

        if not payload.get("ok") or "result" not in payload:
            raise RuntimeError("Telegram getFile returned an invalid payload.")

        file_path = payload["result"].get("file_path")
        if not file_path:
            raise RuntimeError("Telegram getFile payload is missing file_path.")
        return file_path

    async def download_file_bytes(self, file_path: str) -> bytes:
        if not self.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.file_base}/{file_path}")
            response.raise_for_status()
            return response.content

    async def execute_api_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

        method = payload.get("method")
        if not isinstance(method, str) or not method:
            raise RuntimeError("Telegram API payload is missing method.")

        body = {key: value for key, value in payload.items() if key != "method"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.api_base}/{method}",
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def execute_api_calls(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for payload in payloads:
            results.append(await self.execute_api_call(payload))
        return results


def build_telegram_bot_service() -> TelegramBotService:
    return TelegramBotService(settings.TELEGRAM_BOT_TOKEN)


def parse_preview_callback(callback_data: str | None) -> tuple[str, int] | None:
    if not callback_data:
        return None

    prefix, action, raw_id = callback_data.split(":", 2) if callback_data.count(":") == 2 else ("", "", "")
    if prefix != "preview" or action not in {"confirm", "edit", "cancel"}:
        return None

    try:
        preview_id = int(raw_id)
    except ValueError:
        return None

    return action, preview_id
