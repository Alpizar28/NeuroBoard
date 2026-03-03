"""Tests for processing_state_service.

Covers:
- record_processed_media / is_duplicate_media for both image and audio
- Backward-compat aliases (record_processed_image / is_duplicate_image)
- record_log stores the right fields
- Deduplication returns False for unknown hash, True after recording
"""
from __future__ import annotations

import pytest

from app.services.processing_state_service import (
    is_duplicate_image,
    is_duplicate_media,
    record_log,
    record_processed_image,
    record_processed_media,
)


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication: images
# ─────────────────────────────────────────────────────────────────────────────

def test_new_image_hash_is_not_duplicate(db_session) -> None:
    assert is_duplicate_media(db_session, "abc123") is False


def test_recorded_image_is_detected_as_duplicate(db_session) -> None:
    record_processed_media(db_session, "abc123", media_type="image")
    assert is_duplicate_media(db_session, "abc123") is True


def test_different_hash_is_not_duplicate(db_session) -> None:
    record_processed_media(db_session, "abc123", media_type="image")
    assert is_duplicate_media(db_session, "xyz999") is False


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication: audio
# ─────────────────────────────────────────────────────────────────────────────

def test_new_audio_hash_is_not_duplicate(db_session) -> None:
    assert is_duplicate_media(db_session, "audio_hash_001") is False


def test_recorded_audio_is_detected_as_duplicate(db_session) -> None:
    record_processed_media(db_session, "audio_hash_001", media_type="audio")
    assert is_duplicate_media(db_session, "audio_hash_001") is True


def test_media_type_stored_correctly(db_session) -> None:
    from app.models.models import ImageProcessed

    record_processed_media(db_session, "img_hash", media_type="image")
    record_processed_media(db_session, "aud_hash", media_type="audio")

    img_row = db_session.query(ImageProcessed).filter_by(hash="img_hash").first()
    aud_row = db_session.query(ImageProcessed).filter_by(hash="aud_hash").first()

    assert img_row is not None
    assert img_row.media_type == "image"
    assert aud_row is not None
    assert aud_row.media_type == "audio"


# ─────────────────────────────────────────────────────────────────────────────
# Backward-compat aliases
# ─────────────────────────────────────────────────────────────────────────────

def test_record_processed_image_alias(db_session) -> None:
    record_processed_image(db_session, "compat_hash")
    assert is_duplicate_media(db_session, "compat_hash") is True


def test_is_duplicate_image_alias(db_session) -> None:
    assert is_duplicate_image(db_session, "alias_hash") is False
    record_processed_media(db_session, "alias_hash", media_type="image")
    assert is_duplicate_image(db_session, "alias_hash") is True


# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

def test_record_log_stores_status(db_session) -> None:
    from app.models.models import Log

    record_log(db_session, status="image_received", tasks_detected=3)
    row = db_session.query(Log).filter_by(status="image_received").first()
    assert row is not None
    assert row.tasks_detected == 3
    assert row.tasks_created == 0
    assert row.error_message is None


def test_record_log_stores_error_message(db_session) -> None:
    from app.models.models import Log

    record_log(db_session, status="vision_failed", error_message="timeout")
    row = db_session.query(Log).filter_by(status="vision_failed").first()
    assert row is not None
    assert row.error_message == "timeout"


def test_record_log_stores_tasks_created(db_session) -> None:
    from app.models.models import Log

    record_log(db_session, status="google_tasks_created", tasks_detected=2, tasks_created=2)
    row = db_session.query(Log).filter_by(status="google_tasks_created").first()
    assert row is not None
    assert row.tasks_created == 2
