from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.pipeline.contracts import TPT_CONTRACT
from app.scheduling import next_schedule_delay, run_scheduled_once


@asynccontextmanager
async def available_lock():  # type: ignore[no-untyped-def]
    yield True


@asynccontextmanager
async def unavailable_lock():  # type: ignore[no-untyped-def]
    yield False


@pytest.mark.asyncio
async def test_scheduled_run_publishes_only_while_lock_is_held() -> None:
    payload = object()
    fetch = AsyncMock(return_value=payload)
    publish = AsyncMock(return_value=SimpleNamespace(status="unchanged", run_id="scheduled-run-id"))

    result = await run_scheduled_once(
        contract=TPT_CONTRACT,
        lock=available_lock,
        fetch=fetch,
        publish=publish,
    )

    assert result.status == "completed"
    assert result.pipeline_status == "unchanged"
    assert result.run_id == "scheduled-run-id"
    fetch.assert_awaited_once_with(TPT_CONTRACT)
    publish.assert_awaited_once_with(payload, TPT_CONTRACT)


@pytest.mark.asyncio
async def test_scheduled_run_skips_before_fetch_when_lock_is_busy() -> None:
    fetch = AsyncMock()
    publish = AsyncMock()

    result = await run_scheduled_once(
        contract=TPT_CONTRACT,
        lock=unavailable_lock,
        fetch=fetch,
        publish=publish,
    )

    assert result.status == "skipped_locked"
    fetch.assert_not_awaited()
    publish.assert_not_awaited()


def test_schedule_delay_maintains_fixed_interval_without_negative_sleep() -> None:
    assert next_schedule_delay(300, 12.5) == 287.5
    assert next_schedule_delay(300, 301) == 0
