from __future__ import annotations

from datetime import date
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.core.constants import LIST_NAMES
from app.models.schemas import ParsedTask, VisionExtractionPayload
from app.services.classification_service import classify_task
from app.services.date_parser_service import parse_due_date
from app.utils.retry import async_retry


ALLOWED_LIST_NAMES = LIST_NAMES


class VisionService:
    """Thin async client wrapper for a remote vision endpoint."""

    def __init__(self, endpoint: str, timeout_seconds: float | None = None) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.HTTP_TIMEOUT_SECONDS

    async def extract_tasks(self, image_bytes: bytes) -> dict[str, Any]:
        if not self.endpoint:
            raise RuntimeError("VISION_API_URL is not configured.")

        async def _request_extract() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.endpoint,
                    files={"image": ("board.jpg", image_bytes, "image/jpeg")},
                )
                response.raise_for_status()
                return response.json()

        return await async_retry(
            _request_extract,
            max_attempts=settings.HTTP_RETRY_ATTEMPTS,
            backoff_seconds=settings.HTTP_RETRY_BACKOFF_SECONDS,
        )


def build_vision_service(endpoint: str) -> VisionService:
    return VisionService(endpoint)


def parse_vision_payload(
    payload: dict[str, Any],
    *,
    base_date: date | None = None,
) -> tuple[list[ParsedTask], float]:
    try:
        parsed_payload = VisionExtractionPayload.model_validate(payload)
    except ValidationError as exc:
        raise RuntimeError("Vision payload failed schema validation.") from exc

    tasks: list[ParsedTask] = []
    for item in parsed_payload.tasks:
        classification = classify_task(item.text)
        list_name = (
            item.category_hint
            if item.category_hint in ALLOWED_LIST_NAMES
            else classification.list_name
        )

        due_date = None
        warnings = list(item.warnings)
        if item.due_iso:
            try:
                due_date = date.fromisoformat(item.due_iso)
            except ValueError:
                warnings.append("Vision returned an invalid due_iso value.")

        if due_date is None and item.due_text:
            due_date = parse_due_date(item.due_text, base_date=base_date)
            if due_date is None:
                warnings.append("Due date text could not be parsed.")

        tasks.append(
            ParsedTask(
                text=item.text.strip(),
                raw_text=item.text,
                list_name=list_name,
                confidence=item.confidence,
                classification_reason=(
                    f"Vision category hint '{item.category_hint}' accepted."
                    if item.category_hint in ALLOWED_LIST_NAMES
                    else classification.reason
                ),
                due_text=item.due_text,
                due_date=due_date,
                subtasks=[subtask.strip() for subtask in item.subtasks if subtask.strip()],
                warnings=warnings,
            )
        )

    return tasks, parsed_payload.global_confidence
