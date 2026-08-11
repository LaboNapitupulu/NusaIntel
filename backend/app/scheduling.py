from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.pipeline.contracts import IndicatorContract
from app.pipeline.types import PipelineOutcome, RetrievedPayload

FetchPayload = Callable[[IndicatorContract], Awaitable[RetrievedPayload]]
PublishPayload = Callable[[RetrievedPayload, IndicatorContract], Awaitable[PipelineOutcome]]
ScheduleLock = Callable[[], AbstractAsyncContextManager[bool]]

SCHEDULE_ADVISORY_LOCK_KEY = 5648078311158564172


@dataclass(frozen=True, slots=True)
class ScheduledRunResult:
    status: str
    indicator_code: str
    pipeline_status: str | None = None
    run_id: str | None = None


@asynccontextmanager
async def postgres_schedule_lock(
    engine: AsyncEngine,
    *,
    lock_key: int = SCHEDULE_ADVISORY_LOCK_KEY,
) -> AsyncIterator[bool]:
    async with engine.connect() as connection:
        acquired = bool(
            await connection.scalar(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": lock_key},
            )
        )
        try:
            yield acquired
        finally:
            if acquired:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": lock_key},
                )


async def run_scheduled_once(
    *,
    contract: IndicatorContract,
    lock: ScheduleLock,
    fetch: FetchPayload,
    publish: PublishPayload,
) -> ScheduledRunResult:
    async with lock() as acquired:
        if not acquired:
            return ScheduledRunResult(status="skipped_locked", indicator_code=contract.code)
        retrieved = await fetch(contract)
        outcome = await publish(retrieved, contract)
        return ScheduledRunResult(
            status="completed",
            indicator_code=contract.code,
            pipeline_status=outcome.status,
            run_id=outcome.run_id,
        )


def next_schedule_delay(interval_seconds: float, elapsed_seconds: float) -> float:
    return max(0.0, interval_seconds - elapsed_seconds)
