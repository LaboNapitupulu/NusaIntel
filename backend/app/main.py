from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.config import Settings, get_settings
from app.control_tower.service import ControlTowerService
from app.db.session import (
    DatabaseProbe,
    create_database_engine,
    create_database_probe,
    create_session_factory,
)
from app.logging import configure_logging
from app.middleware import (
    AnswerRateLimitMiddleware,
    RequestContextMiddleware,
    RuntimeMetricsMiddleware,
    SecurityHeadersMiddleware,
)
from app.observability import RuntimeMetrics
from app.opportunity.service import OpportunityService
from app.regional_analytics.service import RegionalAnalyticsService
from app.regulasilens.service import CorpusService


def create_app(
    settings: Settings | None = None,
    database_probe: DatabaseProbe | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    engine = None
    if database_probe is None:
        engine = create_database_engine(active_settings.resolved_database_url)
        session_factory = create_session_factory(engine)
        database_probe = create_database_probe(session_factory)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            await engine.dispose()

    application = FastAPI(
        title=active_settings.app_name,
        version="0.7.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.database_probe = database_probe
    application.state.runtime_metrics = RuntimeMetrics()
    application.state.control_tower_service = (
        ControlTowerService(session_factory) if session_factory is not None else None
    )
    application.state.opportunity_service = (
        OpportunityService(session_factory) if session_factory is not None else None
    )
    application.state.regional_analytics_service = (
        RegionalAnalyticsService(session_factory) if session_factory is not None else None
    )
    application.state.regulation_service = (
        CorpusService(
            session_factory,
            answer_timeout_seconds=active_settings.regulation_answer_timeout_seconds,
            maximum_concurrent_answers=active_settings.regulation_maximum_concurrent_answers,
        )
        if session_factory is not None
        else None
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=active_settings.allowed_hosts)
    application.add_middleware(
        AnswerRateLimitMiddleware,
        maximum_requests=active_settings.regulation_answer_rate_limit_requests,
        window_seconds=active_settings.regulation_answer_rate_limit_window_seconds,
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        RuntimeMetricsMiddleware,
        metrics=application.state.runtime_metrics,
    )
    application.add_middleware(
        SecurityHeadersMiddleware,
        production=active_settings.app_env == "production",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
        expose_headers=[
            "Retry-After",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Window",
            "X-Request-ID",
        ],
    )
    application.include_router(api_router)
    return application


app = create_app()
