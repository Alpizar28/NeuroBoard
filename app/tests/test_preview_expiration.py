from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.models import PendingPreview
from app.services.preview_state_service import expire_stale_previews


def _build_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_expires_old_pending_previews() -> None:
    db = _build_test_session()
    preview = PendingPreview(
        image_hash=None,
        payload_json="[]",
        source="test",
        status="pending",
    )
    preview.updated_at = datetime.now(timezone.utc) - timedelta(minutes=120)
    db.add(preview)
    db.commit()

    expired_count = expire_stale_previews(db, max_age_minutes=60)
    db.refresh(preview)

    assert expired_count == 1
    assert preview.status == "expired"


def test_ignores_recent_previews() -> None:
    db = _build_test_session()
    preview = PendingPreview(
        image_hash=None,
        payload_json="[]",
        source="test",
        status="pending",
    )
    db.add(preview)
    db.commit()

    expired_count = expire_stale_previews(db, max_age_minutes=60)
    db.refresh(preview)

    assert expired_count == 0
    assert preview.status == "pending"
