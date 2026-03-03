from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import ImageProcessed, Log


def is_duplicate_media(db: Session, media_hash: str) -> bool:
    """Check if a media hash (image or audio) has been processed before."""
    return (
        db.query(ImageProcessed)
        .filter(ImageProcessed.hash == media_hash)
        .first()
        is not None
    )


# Kept for backward compatibility
def is_duplicate_image(db: Session, image_hash: str) -> bool:
    return is_duplicate_media(db, image_hash)


def record_processed_media(db: Session, media_hash: str, media_type: str = "image") -> ImageProcessed:
    """Record a processed media hash so future duplicates are detected."""
    record = ImageProcessed(hash=media_hash, media_type=media_type)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# Kept for backward compatibility
def record_processed_image(db: Session, image_hash: str) -> ImageProcessed:
    return record_processed_media(db, image_hash, media_type="image")


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
