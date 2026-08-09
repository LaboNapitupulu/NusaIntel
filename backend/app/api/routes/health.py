from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class DependencyStatus(BaseModel):
    status: Literal["ready", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    environment: str
    timestamp: datetime
    dependencies: dict[str, DependencyStatus]


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> JSONResponse:
    database_status: Literal["ready", "unavailable"] = "ready"
    try:
        await request.app.state.database_probe()
    except Exception:
        database_status = "unavailable"

    is_healthy = database_status == "ready"
    body = HealthResponse(
        status="healthy" if is_healthy else "degraded",
        service=request.app.state.settings.app_name,
        environment=request.app.state.settings.app_env,
        timestamp=datetime.now(UTC),
        dependencies={"database": DependencyStatus(status=database_status)},
    )
    return JSONResponse(
        status_code=200 if is_healthy else 503, content=body.model_dump(mode="json")
    )
