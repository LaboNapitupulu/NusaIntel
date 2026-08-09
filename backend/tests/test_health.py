from collections.abc import Awaitable, Callable

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app

DatabaseProbe = Callable[[], Awaitable[None]]


async def healthy_probe() -> None:
    return None


async def unavailable_probe() -> None:
    raise ConnectionError("database unavailable")


async def get_health(probe: DatabaseProbe, request_id: str | None = None):  # type: ignore[no-untyped-def]
    app = create_app(Settings(app_env="test"), database_probe=probe)
    transport = ASGITransport(app=app)
    headers = {"X-Request-ID": request_id} if request_id else None
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/api/v1/health", headers=headers)


@pytest.mark.asyncio
async def test_health_is_healthy_when_database_is_ready() -> None:
    response = await get_health(healthy_probe, request_id="test-correlation-id")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["dependencies"]["database"]["status"] == "ready"
    assert response.headers["X-Request-ID"] == "test-correlation-id"


@pytest.mark.asyncio
async def test_health_is_degraded_when_database_is_unavailable() -> None:
    response = await get_health(unavailable_probe)

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["database"]["status"] == "unavailable"
