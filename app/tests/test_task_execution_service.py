import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.schemas import ParsedTask
from app.services.task_execution_service import execute_preview_tasks


class FakeGoogleTasksService:
    def __init__(self) -> None:
        self.calls = 0
        self.request_log = []

    async def create_task(self, task_payload, *, tasklist="@default", parent=None):
        self.calls += 1
        self.request_log.append(
            {
                "payload": task_payload,
                "tasklist": tasklist,
                "parent": parent,
            }
        )
        return {"id": f"google-{self.calls}", "payload": task_payload}


def _build_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_execute_preview_tasks_is_idempotent() -> None:
    db = _build_test_session()
    service = FakeGoogleTasksService()
    tasks = [
        ParsedTask(
            text="Lavar ropa",
            raw_text="-Lavar ropa",
            list_name="Domesticas",
            confidence=0.9,
            classification_reason="No prefix.",
            subtasks=["Separar blancos", "Tender ropa"],
        )
    ]

    first = asyncio.run(
        execute_preview_tasks(
            db,
            preview_id=10,
            tasks=tasks,
            google_tasks_service=service,
        )
    )
    second = asyncio.run(
        execute_preview_tasks(
            db,
            preview_id=10,
            tasks=tasks,
            google_tasks_service=service,
        )
    )

    assert first.created_count == 3
    assert first.skipped_count == 0
    assert second.created_count == 0
    assert second.skipped_count == 3
    assert service.calls == 3
    assert service.request_log[0]["parent"] is None
    assert service.request_log[0]["tasklist"] == "@default"
    assert service.request_log[1]["parent"] == "google-1"
    assert service.request_log[1]["tasklist"] == "@default"
    assert service.request_log[2]["parent"] == "google-1"
