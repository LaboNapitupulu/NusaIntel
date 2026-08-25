from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.observability import RuntimeMetrics

logger = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        super().__init__(app)
        self._production = production

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=()",
        )
        if self._production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        if request.url.path in {
            "/api/v1/health",
            "/api/v1/live",
            "/api/v1/metrics",
            "/api/v1/ready",
            "/api/v1/regulations/answer",
        }:
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class AnswerRateLimitMiddleware(BaseHTTPMiddleware):
    _answer_path = "/api/v1/regulations/answer"
    _maximum_client_buckets = 4096

    def __init__(self, app: ASGIApp, *, maximum_requests: int, window_seconds: int) -> None:
        super().__init__(app)
        self._maximum_requests = maximum_requests
        self._window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method != "POST" or request.url.path != self._answer_path:
            return await call_next(request)

        client = request.client.host if request.client is not None else "unknown"
        now = time.monotonic()
        async with self._lock:
            boundary = now - self._window_seconds
            if client not in self._buckets and len(self._buckets) >= self._maximum_client_buckets:
                stale_clients = [
                    key
                    for key, values in self._buckets.items()
                    if not values or values[-1] <= boundary
                ]
                for key in stale_clients:
                    self._buckets.pop(key, None)
                if len(self._buckets) >= self._maximum_client_buckets:
                    oldest_client = min(
                        self._buckets,
                        key=lambda key: self._buckets[key][-1],
                    )
                    self._buckets.pop(oldest_client)
            bucket = self._buckets.setdefault(client, deque())
            while bucket and bucket[0] <= boundary:
                bucket.popleft()
            if len(bucket) >= self._maximum_requests:
                retry_after = max(1, math.ceil(bucket[0] + self._window_seconds - now))
                allowed = False
                remaining = 0
            else:
                bucket.append(now)
                retry_after = 0
                allowed = True
                remaining = self._maximum_requests - len(bucket)

        if allowed:
            response = await call_next(request)
        else:
            await logger.awarning(
                "answer_rate_limited",
                path=request.url.path,
                retry_after_seconds=retry_after,
            )
            response = JSONResponse(
                status_code=429,
                content={"detail": "Grounded answer rate limit exceeded"},
            )
            response.headers["Retry-After"] = str(retry_after)

        response.headers["X-RateLimit-Limit"] = str(self._maximum_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self._window_seconds)
        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", "").strip()[:128] or str(uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            await logger.aexception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            raise

        response.headers["X-Request-ID"] = request_id
        await logger.ainfo(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return response


class RuntimeMetricsMiddleware(BaseHTTPMiddleware):
    _metrics_path = "/api/v1/metrics"

    def __init__(self, app: ASGIApp, *, metrics: RuntimeMetrics) -> None:
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == self._metrics_path:
            return await call_next(request)

        await self._metrics.begin_request()
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            await self._metrics.finish_request(
                status_code=500,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
            raise

        await self._metrics.finish_request(
            status_code=response.status_code,
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        return response
