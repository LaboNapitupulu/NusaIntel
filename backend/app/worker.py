from __future__ import annotations

import asyncio

import structlog

from app.config import get_settings
from app.db.session import create_database_engine, create_database_probe, create_session_factory
from app.logging import configure_logging


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = structlog.get_logger(component="worker")
    engine = create_database_engine(settings.resolved_database_url)
    probe = create_database_probe(create_session_factory(engine))
    await logger.ainfo("worker_started", environment=settings.app_env)
    try:
        while True:
            try:
                await probe()
                await logger.ainfo("worker_heartbeat", database_ready=True)
            except Exception as exc:
                await logger.aerror(
                    "worker_heartbeat", database_ready=False, error_type=type(exc).__name__
                )
            await asyncio.sleep(30)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
