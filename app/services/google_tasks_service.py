from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.core.constants import LIST_NAMES
from app.models.schemas import ParsedTask
from app.utils.retry import async_retry


class GoogleTasksService:
    """Async client for the Google Tasks API v1 with OAuth2 refresh support.

    The access_token is refreshed automatically on 401 responses.
    After each refresh the new token is persisted to the database via
    the optional `_persist_token` callback so subsequent requests in
    other worker processes can reuse it without hitting the token endpoint.
    """

    def __init__(
        self,
        access_token: str = "",
        *,
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        token_url: str | None = None,
        timeout_seconds: float | None = None,
        retry_attempts: int | None = None,
        retry_backoff_seconds: float | None = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        # Use settings as single source of truth; constructor args override for tests
        self.token_url = token_url if token_url is not None else settings.GOOGLE_OAUTH_TOKEN_URL
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.HTTP_TIMEOUT_SECONDS
        self.retry_attempts = retry_attempts if retry_attempts is not None else settings.HTTP_RETRY_ATTEMPTS
        self.retry_backoff_seconds = retry_backoff_seconds if retry_backoff_seconds is not None else settings.HTTP_RETRY_BACKOFF_SECONDS

    def _has_refresh_credentials(self) -> bool:
        return bool(
            self.refresh_token
            and self.client_id
            and self.client_secret
            and self.token_url
        )

    async def _refresh_access_token(self, db=None) -> str:
        """Refresh the OAuth access token and optionally persist it to the DB."""
        if not self._has_refresh_credentials():
            raise RuntimeError("Google OAuth refresh credentials are not configured.")

        async def _request_refresh() -> dict[str, Any]:
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
                return response.json()

        payload = await async_retry(
            _request_refresh,
            max_attempts=self.retry_attempts,
            backoff_seconds=self.retry_backoff_seconds,
        )

        refreshed_token = payload.get("access_token")
        if not refreshed_token:
            raise RuntimeError("Google OAuth token refresh did not return access_token.")

        self.access_token = refreshed_token

        # Persist to DB so subsequent requests reuse the token
        if db is not None:
            _persist_oauth_token(db, access_token=refreshed_token, expires_in=payload.get("expires_in"))

        return refreshed_token

    async def create_task(
        self,
        task_payload: dict[str, Any],
        *,
        tasklist: str = "@default",
        parent: str | None = None,
        db=None,
    ) -> dict[str, Any]:
        if not self.access_token and self._has_refresh_credentials():
            await self._refresh_access_token(db=db)

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
            await self._refresh_access_token(db=db)
            return await async_retry(
                _request_create,
                max_attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )


def _persist_oauth_token(db, *, access_token: str, expires_in: int | None) -> None:
    """Save the refreshed access token to the oauth_tokens table."""
    from app.models.models import OAuthToken

    expires_at: datetime | None = None
    if expires_in:
        expires_at = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        expires_at = expires_at + timedelta(seconds=int(expires_in) - 60)  # 60s safety margin

    existing = (
        db.query(OAuthToken)
        .filter(OAuthToken.provider == "google")
        .first()
    )
    if existing:
        existing.access_token = access_token
        existing.expires_at = expires_at
        existing.timestamp = datetime.now(timezone.utc)
        db.add(existing)
    else:
        record = OAuthToken(
            provider="google",
            access_token=access_token,
            expires_at=expires_at,
        )
        db.add(record)
    db.commit()


def load_cached_access_token(db) -> str | None:
    """Load a non-expired access token from the DB cache, if available."""
    from app.models.models import OAuthToken

    record = (
        db.query(OAuthToken)
        .filter(OAuthToken.provider == "google")
        .first()
    )
    if not record or not record.access_token:
        return None
    if record.expires_at and record.expires_at < datetime.now(timezone.utc):
        return None
    return record.access_token


def build_google_tasks_service(db=None) -> GoogleTasksService:
    # Try to use a cached (non-expired) access token from the DB
    access_token = settings.GOOGLE_TASKS_ACCESS_TOKEN
    if db is not None:
        cached = load_cached_access_token(db)
        if cached:
            access_token = cached

    return GoogleTasksService(
        access_token,
        refresh_token=settings.GOOGLE_TASKS_REFRESH_TOKEN,
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
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
