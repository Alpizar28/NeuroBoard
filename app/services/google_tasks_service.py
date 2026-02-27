from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.models.schemas import ParsedTask


class GoogleTasksService:
    """Small client placeholder for future Google Tasks integration."""

    def __init__(self, access_token: str = "", timeout_seconds: float = 8.0) -> None:
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    async def create_task(
        self,
        task_payload: dict[str, Any],
        *,
        tasklist: str = "@default",
        parent: str | None = None,
    ) -> dict[str, Any]:
        if not self.access_token:
            raise RuntimeError("Google Tasks access token is not configured.")

        params: dict[str, Any] = {}
        if parent:
            params["parent"] = parent

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist}/tasks",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params,
                json=task_payload,
            )
            response.raise_for_status()
            return response.json()


def build_google_tasks_service() -> GoogleTasksService:
    return GoogleTasksService(settings.GOOGLE_TASKS_ACCESS_TOKEN)


def build_google_task_payload(task: ParsedTask) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": task.text}
    notes: list[str] = []

    if task.subtasks:
        notes.append("Subtasks:")
        notes.extend(f"- {subtask}" for subtask in task.subtasks)

    if task.warnings:
        notes.append("Warnings:")
        notes.extend(f"- {warning}" for warning in task.warnings)

    if notes:
        payload["notes"] = "\n".join(notes)

    if task.due_date:
        payload["due"] = f"{task.due_date.isoformat()}T00:00:00.000Z"

    return payload


def build_google_subtask_payload(subtask_text: str) -> dict[str, Any]:
    return {"title": subtask_text}


def resolve_google_tasklist_id(list_name: str) -> str:
    mapping = {
        "Proyectos": settings.GOOGLE_TASKLIST_PROYECTOS_ID,
        "Jokem": settings.GOOGLE_TASKLIST_JOKEM_ID,
        "Personales": settings.GOOGLE_TASKLIST_PERSONALES_ID,
        "Domesticas": settings.GOOGLE_TASKLIST_DOMESTICAS_ID,
    }
    return mapping.get(list_name, "@default") or "@default"
