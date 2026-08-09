from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx

from app.bps.errors import (
    BPSAuthenticationError,
    BPSConfigurationError,
    BPSDataUnavailableError,
    BPSPayloadError,
    BPSRateLimitError,
    BPSResponseError,
    BPSTransientError,
)
from app.config import Settings
from app.pipeline.contracts import IndicatorContract
from app.pipeline.types import RetrievedPayload

Sleep = Callable[[float], Awaitable[None]]


class BPSClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        random_source: Callable[[], float] = random.random,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._random = random_source
        self._rate_lock = asyncio.Lock()
        self._last_request_started = 0.0
        self._client = httpx.AsyncClient(
            base_url=f"{settings.bps_base_url.rstrip('/')}/",
            timeout=httpx.Timeout(settings.bps_timeout_seconds),
            headers={
                "Accept": "application/json",
                "User-Agent": settings.bps_user_agent,
            },
            transport=transport,
        )

    async def __aenter__(self) -> BPSClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def fetch(self, contract: IndicatorContract) -> RetrievedPayload:
        if self._settings.bps_api_key is None:
            raise BPSConfigurationError("BPS_API_KEY is required for a live request.")

        safe_parameters = contract.safe_parameters
        request_parameters = {
            **safe_parameters,
            "key": self._settings.bps_api_key.get_secret_value(),
        }
        for attempt in range(1, self._settings.bps_max_attempts + 1):
            await self._wait_for_rate_limit()
            try:
                response = await self._client.get("list", params=request_parameters)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self._settings.bps_max_attempts:
                    raise BPSTransientError(
                        "BPS request failed after the configured attempts."
                    ) from None
                await self._sleep(self._retry_delay(attempt))
                continue

            if response.status_code in {401, 403}:
                raise BPSAuthenticationError("BPS rejected the configured credential.")
            if response.status_code == 429:
                if attempt == self._settings.bps_max_attempts:
                    raise BPSRateLimitError("BPS rate limit persisted after retries.")
                await self._sleep(self._retry_after(response, attempt))
                continue
            if response.status_code >= 500:
                if attempt == self._settings.bps_max_attempts:
                    raise BPSTransientError("BPS server error persisted after retries.")
                await self._sleep(self._retry_delay(attempt))
                continue
            if response.status_code >= 400:
                raise BPSResponseError(f"BPS returned HTTP {response.status_code}.")
            try:
                return self._parse_response(response, safe_parameters)
            except BPSPayloadError:
                if attempt == self._settings.bps_max_attempts:
                    raise
                await self._sleep(self._retry_delay(attempt))

        raise BPSTransientError("BPS request did not produce a response.")

    async def _wait_for_rate_limit(self) -> None:
        async with self._rate_lock:
            now = time.monotonic()
            remaining = self._settings.bps_min_interval_seconds - (now - self._last_request_started)
            if remaining > 0:
                await self._sleep(remaining)
            self._last_request_started = time.monotonic()

    def _retry_delay(self, attempt: int) -> float:
        retry_base = float(self._settings.bps_retry_base_seconds)
        base = retry_base * (2 ** (attempt - 1))
        jitter = float(self._random()) * retry_base / 4
        return float(base + jitter)

    def _retry_after(self, response: httpx.Response, attempt: int) -> float:
        try:
            server_delay = float(response.headers.get("Retry-After", "0"))
        except ValueError:
            server_delay = 0
        return max(server_delay, self._retry_delay(attempt))

    def _parse_response(
        self,
        response: httpx.Response,
        safe_parameters: dict[str, str],
    ) -> RetrievedPayload:
        body = response.content
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BPSPayloadError("BPS response was not valid UTF-8 JSON.") from None
        if not isinstance(payload, dict):
            raise BPSPayloadError("BPS response root must be an object.")

        if payload.get("status") != "OK":
            message = str(payload.get("message", "")).casefold()
            if "key" in message or "token" in message:
                raise BPSAuthenticationError("BPS rejected the configured credential.")
            raise BPSResponseError("BPS returned an error response.")
        if payload.get("data-availability") != "available":
            raise BPSDataUnavailableError("BPS reported that the requested data is unavailable.")
        data_content = payload.get("datacontent")
        if not isinstance(data_content, dict):
            raise BPSPayloadError("BPS datacontent must be an object.")

        selected_headers = {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower()
            in {
                "content-type",
                "etag",
                "last-modified",
                "x-ratelimit-limit",
                "x-ratelimit-remaining",
            }
        }
        return RetrievedPayload(
            endpoint=f"{self._settings.bps_base_url.rstrip('/')}/list",
            safe_parameters=dict(safe_parameters),
            http_status=response.status_code,
            response_headers=selected_headers,
            retrieved_at=datetime.now(UTC),
            body_text=body.decode("utf-8"),
            payload=payload,
            checksum=hashlib.sha256(body).hexdigest(),
            byte_count=len(body),
            row_count=len(data_content),
        )
