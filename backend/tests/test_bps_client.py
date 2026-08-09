from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.bps.client import BPSClient
from app.bps.errors import BPSAuthenticationError, BPSTransientError
from app.config import Settings
from app.pipeline.contracts import TPT_CONTRACT

FIXTURE_PATH = (
    Path(__file__).parents[2] / "tests" / "fixtures" / "bps" / "tpt_august_543_2023_2025_live.json"
)


async def _no_sleep(_: float) -> None:
    return None


@pytest.mark.asyncio
async def test_client_retries_transient_failure_and_never_exposes_key() -> None:
    fixture = json.loads(FIXTURE_PATH.read_bytes())
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.url.path == "/v1/api/list"
        assert request.url.params["key"] == "super-secret"
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=fixture)

    settings = Settings(
        bps_api_key="super-secret",
        bps_min_interval_seconds=0,
        bps_retry_base_seconds=0,
    )
    async with BPSClient(
        settings,
        transport=httpx.MockTransport(handler),
        sleep=_no_sleep,
    ) as client:
        retrieved = await client.fetch(TPT_CONTRACT)

    assert attempts == 2
    assert "key" not in retrieved.safe_parameters
    assert "super-secret" not in retrieved.source_identity
    assert retrieved.row_count == 113


@pytest.mark.asyncio
async def test_client_authentication_error_is_credential_safe() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    settings = Settings(bps_api_key="super-secret", bps_min_interval_seconds=0)
    async with BPSClient(settings, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BPSAuthenticationError) as captured:
            await client.fetch(TPT_CONTRACT)

    assert "super-secret" not in str(captured.value)


@pytest.mark.asyncio
async def test_client_retries_malformed_success_response() -> None:
    fixture = json.loads(FIXTURE_PATH.read_bytes())
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(200, content=b"not-json")
        return httpx.Response(200, json=fixture)

    settings = Settings(
        bps_api_key="super-secret",
        bps_min_interval_seconds=0,
        bps_retry_base_seconds=0,
    )
    async with BPSClient(
        settings,
        transport=httpx.MockTransport(handler),
        sleep=_no_sleep,
    ) as client:
        retrieved = await client.fetch(TPT_CONTRACT)

    assert attempts == 2
    assert retrieved.row_count == 113


@pytest.mark.asyncio
async def test_client_timeout_has_bounded_attempts() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timeout", request=request)

    settings = Settings(
        bps_api_key="super-secret",
        bps_max_attempts=2,
        bps_min_interval_seconds=0,
        bps_retry_base_seconds=0,
    )
    async with BPSClient(
        settings,
        transport=httpx.MockTransport(handler),
        sleep=_no_sleep,
    ) as client:
        with pytest.raises(BPSTransientError):
            await client.fetch(TPT_CONTRACT)

    assert attempts == 2
