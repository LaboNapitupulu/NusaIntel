from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import Settings, get_settings
from app.db.session import (
    DatabaseProbe,
    create_database_engine,
    create_database_probe,
    create_session_factory,
)
from app.logging import configure_logging
from app.middleware import RequestContextMiddleware


def create_app(
    settings: Settings | None = None,
    database_probe: DatabaseProbe | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    engine = None
    if database_probe is None:
        engine = create_database_engine(active_settings.resolved_database_url)
        database_probe = create_database_probe(create_session_factory(engine))

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            await engine.dispose()

    application = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.database_probe = database_probe
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )
    application.include_router(api_router)
    return application


app = create_app()
