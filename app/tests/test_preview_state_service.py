from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.schemas import ParsedTask
from app.services.preview_state_service import (
    create_pending_preview,
    get_pending_preview,
    load_preview_tasks,
    replace_preview_tasks,
    update_preview_status,
)


def _build_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_persists_and_loads_pending_preview() -> None:
    db = _build_test_session()
    preview = create_pending_preview(
        db,
        tasks=[
            ParsedTask(
                text="Lavar ropa",
                raw_text="-Lavar ropa",
                list_name="Domesticas",
                confidence=0.9,
                classification_reason="No prefix.",
            )
        ],
        image_hash="abc123",
        source="fallback_text",
    )

    stored = get_pending_preview(db, preview.id)
    assert stored is not None
    tasks = load_preview_tasks(stored)
    assert tasks[0].text == "Lavar ropa"
    assert tasks[0].list_name == "Domesticas"


def test_updates_preview_status() -> None:
    db = _build_test_session()
    preview = create_pending_preview(
        db,
        tasks=[],
        image_hash=None,
        source="vision",
    )

    updated = update_preview_status(db, preview=preview, status="confirmed")
    assert updated.status == "confirmed"


def test_replaces_preview_payload_in_place() -> None:
    db = _build_test_session()
    preview = create_pending_preview(
        db,
        tasks=[],
        image_hash=None,
        source="vision",
    )

    updated = replace_preview_tasks(
        db,
        preview=preview,
        tasks=[
            ParsedTask(
                text="Comprar cafe",
                raw_text="-Comprar cafe",
                list_name="Domesticas",
                confidence=0.9,
                classification_reason="No prefix.",
            )
        ],
        source="manual_edit",
        status="pending",
    )

    reloaded = load_preview_tasks(updated)
    assert updated.source == "manual_edit"
    assert reloaded[0].text == "Comprar cafe"
