import asyncio

import httpx

from app.utils.retry import async_retry


def test_async_retry_succeeds_after_transient_failure() -> None:
    state = {"calls": 0}

    async def operation():
        state["calls"] += 1
        if state["calls"] == 1:
            raise httpx.ConnectError("temporary failure")
        return "ok"

    result = asyncio.run(async_retry(operation, max_attempts=3, backoff_seconds=0))
    assert result == "ok"
    assert state["calls"] == 2


def test_async_retry_stops_on_non_retryable_error() -> None:
    state = {"calls": 0}

    async def operation():
        state["calls"] += 1
        raise RuntimeError("do not retry")

    try:
        asyncio.run(async_retry(operation, max_attempts=3, backoff_seconds=0))
    except RuntimeError as exc:
        assert str(exc) == "do not retry"
    else:
        raise AssertionError("Expected RuntimeError to be raised.")

    assert state["calls"] == 1
