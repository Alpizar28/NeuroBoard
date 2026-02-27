from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.models.schemas import ParsedTask
from app.utils.retry import async_retry


class GoogleTasksService:
    """Small client placeholder for future Google Tasks integration."""

    def __init__(
        self,
        access_token: str = "",
        *,
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        token_url: str = "https://oauth2.googleapis.com/token",
        timeout_seconds: float = 8.0,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.25,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    def _has_refresh_credentials(self) -> bool:
        return bool(
            self.refresh_token
            and self.client_id
            and self.client_secret
            and self.token_url
        )

    async def _refresh_access_token(self) -> str:
        if not self._has_refresh_credentials():
            raise RuntimeError("Google OAuth refresh credentials are not configured.")

        async def _request_refresh() -> str:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                response.raise_for_status()
                payload = response.json()

            refreshed_token = payload.get("access_token")
            if not refreshed_token:
                raise RuntimeError("Google OAuth token refresh did not return access_token.")

            self.access_token = refreshed_token
            return refreshed_token

        return await async_retry(
            _request_refresh,
            max_attempts=self.retry_attempts,
            backoff_seconds=self.retry_backoff_seconds,
        )

    async def create_task(
        self,
        task_payload: dict[str, Any],
        *,
        tasklist: str = "@default",
        parent: str | None = None,
    ) -> dict[str, Any]:
        if not self.access_token and self._has_refresh_credentials():
            await self._refresh_access_token()

        if not self.access_token:
            raise RuntimeError("Google Tasks access token is not configured.")

        params: dict[str, Any] = {}
        if parent:
            params["parent"] = parent

        async def _request_create() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist}/tasks",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params=params,
                    json=task_payload,
                )
                response.raise_for_status()
                return response.json()

        try:
            return await async_retry(
                _request_create,
                max_attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 401 or not self._has_refresh_credentials():
                raise
            await self._refresh_access_token()
            return await async_retry(
                _request_create,
                max_attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )


def build_google_tasks_service() -> GoogleTasksService:
    return GoogleTasksService(
        settings.GOOGLE_TASKS_ACCESS_TOKEN,
        refresh_token=settings.GOOGLE_TASKS_REFRESH_TOKEN,
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        token_url=settings.GOOGLE_OAUTH_TOKEN_URL,
        retry_attempts=settings.HTTP_RETRY_ATTEMPTS,
        retry_backoff_seconds=settings.HTTP_RETRY_BACKOFF_SECONDS,
    )


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
