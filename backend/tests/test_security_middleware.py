from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


async def healthy_probe() -> None:
    return None


class AnswerService:
    async def answer(self, question: str, **_: Any) -> dict[str, Any]:
        return {
            "question": question,
            "answerable": False,
            "answer": "Evidence tidak cukup.",
            "citations": [],
        }


@pytest.mark.asyncio
async def test_answer_rate_limit_fails_with_retry_contract() -> None:
    settings = Settings(
        app_env="test",
        regulation_answer_rate_limit_requests=1,
        regulation_answer_rate_limit_window_seconds=60,
    )
    app = create_app(settings, database_probe=healthy_probe)
    app.state.regulation_service = AnswerService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/api/v1/regulations/answer",
            json={"question": "Apa hak Subjek Data Pribadi?"},
        )
        limited = await client.post(
            "/api/v1/regulations/answer",
            json={"question": "Apa kewajiban Pengendali Data Pribadi?"},
            headers={"X-Request-ID": "rate-limit-test"},
        )
        health = await client.get("/api/v1/live")

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Remaining"] == "0"
    assert first.headers["Cache-Control"] == "no-store"
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Grounded answer rate limit exceeded"
    assert int(limited.headers["Retry-After"]) >= 1
    assert limited.headers["X-Request-ID"] == "rate-limit-test"
    assert health.status_code == 200


@pytest.mark.asyncio
async def test_security_headers_and_trusted_hosts() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://user:password@db:5432/nusa_intel",
        cors_origins=["https://app.example.test"],
        allowed_hosts=["api.example.test", "test"],
    )
    app = create_app(settings, database_probe=healthy_probe)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/live")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://untrusted.example.test"
    ) as client:
        rejected = await client.get("/api/v1/live")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=31536000")
    assert rejected.status_code == 400
