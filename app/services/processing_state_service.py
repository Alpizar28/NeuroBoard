from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import ImageProcessed, Log


def is_duplicate_image(db: Session, image_hash: str) -> bool:
    return (
        db.query(ImageProcessed)
        .filter(ImageProcessed.hash == image_hash)
        .first()
        is not None
    )


def record_processed_image(db: Session, image_hash: str) -> ImageProcessed:
    record = ImageProcessed(hash=image_hash)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def record_log(
    db: Session,
    *,
    status: str,
    tasks_detected: int = 0,
    tasks_created: int = 0,
    error_message: str | None = None,
) -> Log:
    log = Log(
        status=status,
        tasks_detected=tasks_detected,
        tasks_created=tasks_created,
        error_message=error_message,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
