from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.models import PreviewTaskCreation
from app.models.schemas import ParsedTask
from app.services.google_tasks_service import (
    GoogleTasksService,
    build_google_subtask_payload,
    build_google_task_payload,
    resolve_google_tasklist_id,
)


@dataclass(frozen=True)
class TaskExecutionResult:
    created_count: int
    skipped_count: int
    created_ids: list[str]


def _task_key(preview_id: int, index: int) -> str:
    return f"{preview_id}:{index}"


def _subtask_key(preview_id: int, task_index: int, subtask_index: int) -> str:
    return f"{preview_id}:{task_index}:{subtask_index}"


def _find_existing_creation(
    db: Session,
    *,
    task_key: str,
) -> PreviewTaskCreation | None:
    return (
        db.query(PreviewTaskCreation)
        .filter(PreviewTaskCreation.task_key == task_key)
        .first()
    )


def _record_creation(
    db: Session,
    *,
    preview_id: int,
    task_key: str,
    google_task_id: str,
    list_name: str,
) -> PreviewTaskCreation:
    creation = PreviewTaskCreation(
        preview_id=preview_id,
        task_key=task_key,
        google_task_id=google_task_id,
        list_name=list_name,
    )
    db.add(creation)
    db.commit()
    db.refresh(creation)
    return creation


async def execute_preview_tasks(
    db: Session,
    *,
    preview_id: int,
    tasks: list[ParsedTask],
    google_tasks_service: GoogleTasksService,
) -> TaskExecutionResult:
    created_count = 0
    skipped_count = 0
    created_ids: list[str] = []

    for index, task in enumerate(tasks):
        tasklist_id = resolve_google_tasklist_id(task.list_name)
        task_key = _task_key(preview_id, index)
        existing = _find_existing_creation(db, task_key=task_key)
        parent_google_task_id: str | None = None
        if existing is not None:
            skipped_count += 1
            created_ids.append(existing.google_task_id)
            parent_google_task_id = existing.google_task_id
        else:
            response = await google_tasks_service.create_task(
                build_google_task_payload(task),
                tasklist=tasklist_id,
            )
            google_task_id = response.get("id")
            if not google_task_id:
                raise RuntimeError("Google Tasks response is missing task id.")

            _record_creation(
                db,
                preview_id=preview_id,
                task_key=task_key,
                google_task_id=google_task_id,
                list_name=task.list_name,
            )
            created_count += 1
            created_ids.append(google_task_id)
            parent_google_task_id = google_task_id

        for subtask_index, subtask in enumerate(task.subtasks):
            subtask_key = _subtask_key(preview_id, index, subtask_index)
            existing_subtask = _find_existing_creation(db, task_key=subtask_key)
            if existing_subtask is not None:
                skipped_count += 1
                created_ids.append(existing_subtask.google_task_id)
                continue

            if not parent_google_task_id:
                raise RuntimeError("Cannot create subtask without parent task id.")

            subtask_response = await google_tasks_service.create_task(
                build_google_subtask_payload(subtask),
                tasklist=tasklist_id,
                parent=parent_google_task_id,
            )
            subtask_google_task_id = subtask_response.get("id")
            if not subtask_google_task_id:
                raise RuntimeError("Google Tasks response is missing subtask id.")

            _record_creation(
                db,
                preview_id=preview_id,
                task_key=subtask_key,
                google_task_id=subtask_google_task_id,
                list_name=task.list_name,
            )
            created_count += 1
            created_ids.append(subtask_google_task_id)

    return TaskExecutionResult(
        created_count=created_count,
        skipped_count=skipped_count,
        created_ids=created_ids,
    )
