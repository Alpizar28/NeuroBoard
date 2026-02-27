from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.models import PendingPreview
from app.models.schemas import ParsedTask


def create_pending_preview(
    db: Session,
    *,
    tasks: list[ParsedTask],
    image_hash: str | None,
    source: str,
) -> PendingPreview:
    payload_json = json.dumps(
        [task.model_dump(mode="json") for task in tasks],
        ensure_ascii=True,
    )
    preview = PendingPreview(
        image_hash=image_hash,
        payload_json=payload_json,
        source=source,
        status="pending",
    )
    db.add(preview)
    db.commit()
    db.refresh(preview)
    return preview


def get_pending_preview(db: Session, preview_id: int) -> PendingPreview | None:
    return (
        db.query(PendingPreview)
        .filter(PendingPreview.id == preview_id)
        .first()
    )


def load_preview_tasks(preview: PendingPreview) -> list[ParsedTask]:
    raw_tasks = json.loads(preview.payload_json)
    return [ParsedTask.model_validate(item) for item in raw_tasks]


def update_preview_status(
    db: Session,
    *,
    preview: PendingPreview,
    status: str,
) -> PendingPreview:
    preview.status = status
    db.add(preview)
    db.commit()
    db.refresh(preview)
    return preview


def replace_preview_tasks(
    db: Session,
    *,
    preview: PendingPreview,
    tasks: list[ParsedTask],
    source: str | None = None,
    status: str = "pending",
) -> PendingPreview:
    preview.payload_json = json.dumps(
        [task.model_dump(mode="json") for task in tasks],
        ensure_ascii=True,
    )
    preview.status = status
    if source is not None:
        preview.source = source
    db.add(preview)
    db.commit()
    db.refresh(preview)
    return preview


def expire_stale_previews(
    db: Session,
    *,
    max_age_minutes: int,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    stale_previews = (
        db.query(PendingPreview)
        .filter(PendingPreview.status.in_(["pending", "editing", "confirmed", "creation_failed"]))
        .filter(PendingPreview.updated_at < cutoff)
        .all()
    )

    for preview in stale_previews:
        preview.status = "expired"
        db.add(preview)

    if stale_previews:
        db.commit()

    return len(stale_previews)


def list_previews(
    db: Session,
    *,
    status: str | None = None,
    preview_id: int | None = None,
    image_hash: str | None = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    limit: int = 50,
) -> list[PendingPreview]:
    query = db.query(PendingPreview).order_by(PendingPreview.updated_at.desc())
    if status:
        query = query.filter(PendingPreview.status == status)
    if preview_id is not None:
        query = query.filter(PendingPreview.id == preview_id)
    if image_hash:
        query = query.filter(PendingPreview.image_hash == image_hash)
    if updated_from is not None:
        query = query.filter(PendingPreview.updated_at >= updated_from)
    if updated_to is not None:
        query = query.filter(PendingPreview.updated_at <= updated_to)
    return query.limit(limit).all()
