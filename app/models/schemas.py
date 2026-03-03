from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParsedTask(BaseModel):
    text: str
    raw_text: str
    list_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    classification_reason: str
    due_text: str | None = None
    due_date: date | None = None
    subtasks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    status: str
    tasks: list[ParsedTask] = Field(default_factory=list)
    duplicate: bool = False
    media_hash: str | None = None
    # Kept for backwards compatibility
    image_hash: str | None = None
    preview_id: int | None = None
    action: str | None = None
    message: str | None = None
    reply_markup: dict[str, Any] | None = None
    telegram_api_calls: list[dict[str, Any]] = Field(default_factory=list)
    telegram_api_results: list[dict[str, Any]] = Field(default_factory=list)


class PreviewAdminItem(BaseModel):
    id: int
    status: str
    source: str
    media_hash: str | None = None
    # Kept for backwards compatibility
    image_hash: str | None = None
    task_count: int
    created_at: str
    updated_at: str


class PreviewAdminListResponse(BaseModel):
    items: list[PreviewAdminItem] = Field(default_factory=list)
    total: int = 0
    status_filter: str | None = None
    preview_id_filter: int | None = None
    image_hash_filter: str | None = None
    updated_from_filter: str | None = None
    updated_to_filter: str | None = None


class TelegramWebhookPayload(BaseModel):
    """Production webhook payload — no test fields allowed."""
    model_config = ConfigDict(extra="ignore")

    update_id: int | None = None
    message: dict[str, Any] | None = None
    callback_query: dict[str, Any] | None = None


class TelegramWebhookTestPayload(BaseModel):
    """Test-only payload that bypasses image download via mock_lines.
    Used by the /webhook/test endpoint which is disabled in production."""
    update_id: int | None = None
    message: dict[str, Any] | None = None
    callback_query: dict[str, Any] | None = None
    mock_lines: list[str] = Field(default_factory=list)


class TelegramFile(BaseModel):
    file_id: str
    file_size: int | None = None


class TelegramGetFileResponse(BaseModel):
    ok: bool
    result: dict[str, Any]


class VisionTaskPayload(BaseModel):
    text: str
    category_hint: str | None = None
    due_text: str | None = None
    due_iso: str | None = None
    subtasks: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class VisionExtractionPayload(BaseModel):
    tasks: list[VisionTaskPayload] = Field(default_factory=list)
    global_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
