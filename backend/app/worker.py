from __future__ import annotations

import asyncio
import time

import structlog

from app.bps.client import BPSClient
from app.config import get_settings
from app.db.session import create_database_engine, create_database_probe, create_session_factory
from app.logging import configure_logging
from app.pipeline.contracts import CONTRACTS
from app.pipeline.service import PipelineService
from app.scheduling import next_schedule_delay, postgres_schedule_lock, run_scheduled_once


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = structlog.get_logger(component="worker")
    engine = create_database_engine(settings.resolved_database_url)
    session_factory = create_session_factory(engine)
    probe = create_database_probe(session_factory)
    await logger.ainfo("worker_started", environment=settings.app_env)
    try:
        if not settings.bps_schedule_enabled:
            while True:
                try:
                    await probe()
                    await logger.ainfo(
                        "worker_heartbeat",
                        database_ready=True,
                        scheduler_enabled=False,
                    )
                except Exception as exc:
                    await logger.aerror(
                        "worker_heartbeat",
                        database_ready=False,
                        scheduler_enabled=False,
                        error_type=type(exc).__name__,
                    )
                await asyncio.sleep(30)

        contract = CONTRACTS[settings.bps_schedule_indicator]
        pipeline = PipelineService(session_factory)
        async with BPSClient(settings) as client:
            while True:
                started = time.monotonic()
                try:
                    result = await run_scheduled_once(
                        contract=contract,
                        lock=lambda: postgres_schedule_lock(engine),
                        fetch=client.fetch,
                        publish=pipeline.run,
                    )
                    await logger.ainfo(
                        "scheduled_pipeline",
                        status=result.status,
                        indicator_code=result.indicator_code,
                        pipeline_status=result.pipeline_status,
                        run_id=result.run_id,
                    )
                except Exception as exc:
                    await logger.aerror(
                        "scheduled_pipeline",
                        status="failed",
                        indicator_code=contract.code,
                        error_type=type(exc).__name__,
                    )
                delay = next_schedule_delay(
                    settings.bps_schedule_interval_seconds,
                    time.monotonic() - started,
                )
                await asyncio.sleep(delay)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
