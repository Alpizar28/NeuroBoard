from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx


T = TypeVar("T")


def _default_should_retry_exception(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or 500 <= status_code <= 599

    return isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RequestError,
        ),
    )


async def async_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 0.25,
    should_retry_exception: Callable[[Exception], bool] | None = None,
) -> T:
    predicate = should_retry_exception or _default_should_retry_exception
    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001
            last_exception = exc
            if attempt >= max_attempts or not predicate(exc):
                raise
            await asyncio.sleep(backoff_seconds * attempt)

    if last_exception is not None:
        raise last_exception

    raise RuntimeError("Retry helper exited without result or exception.")
