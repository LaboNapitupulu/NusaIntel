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


async def get_system_endpoint(probe: DatabaseProbe, path: str):  # type: ignore[no-untyped-def]
    app = create_app(Settings(app_env="test"), database_probe=probe)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


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


@pytest.mark.asyncio
async def test_liveness_does_not_depend_on_database_readiness() -> None:
    app = create_app(
        Settings(app_env="test", release_sha="test-release"),
        database_probe=unavailable_probe,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.json()["version"] == "0.7.0"
    assert response.json()["release"] == "test-release"
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.asyncio
async def test_readiness_fails_closed_when_database_is_unavailable() -> None:
    response = await get_system_endpoint(unavailable_probe, "/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.asyncio
async def test_runtime_metrics_are_bounded_and_release_aware() -> None:
    app = create_app(
        Settings(app_env="test", release_sha="metrics-release"),
        database_probe=healthy_probe,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/live")
        await client.get("/api/v1/does-not-exist")
        response = await client.get("/api/v1/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["release"] == "metrics-release"
    assert payload["total_requests"] == 2
    assert payload["failed_requests"] == 0
    assert payload["in_flight_requests"] == 0
    assert payload["status_counts"] == {"200": 1, "404": 1}
    assert payload["latency_ms"]["sample_count"] == 2
    assert payload["latency_ms"]["p95"] is not None
    assert response.headers["Cache-Control"] == "no-store"
