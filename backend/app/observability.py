from __future__ import annotations

import asyncio
import math
import time
from collections import Counter, deque
from datetime import UTC, datetime


class RuntimeMetrics:
    """Bounded, process-local diagnostics for the public-beta runtime."""

    _maximum_latency_samples = 512

    def __init__(self) -> None:
        self.started_at = datetime.now(UTC)
        self._started_monotonic = time.monotonic()
        self._total_requests = 0
        self._failed_requests = 0
        self._in_flight = 0
        self._status_counts: Counter[int] = Counter()
        self._latency_samples_ms: deque[float] = deque(maxlen=self._maximum_latency_samples)
        self._lock = asyncio.Lock()

    async def begin_request(self) -> None:
        async with self._lock:
            self._in_flight += 1

    async def finish_request(self, *, status_code: int, duration_ms: float) -> None:
        async with self._lock:
            self._in_flight = max(0, self._in_flight - 1)
            self._total_requests += 1
            self._status_counts[status_code] += 1
            self._latency_samples_ms.append(max(0.0, duration_ms))
            if status_code >= 500:
                self._failed_requests += 1

    async def snapshot(self) -> dict[str, object]:
        async with self._lock:
            samples = sorted(self._latency_samples_ms)
            return {
                "started_at": self.started_at,
                "uptime_seconds": round(max(0.0, time.monotonic() - self._started_monotonic), 3),
                "total_requests": self._total_requests,
                "failed_requests": self._failed_requests,
                "in_flight_requests": self._in_flight,
                "status_counts": {
                    str(status): count for status, count in sorted(self._status_counts.items())
                },
                "latency_ms": {
                    "sample_count": len(samples),
                    "p50": self._percentile(samples, 0.50),
                    "p95": self._percentile(samples, 0.95),
                    "maximum": round(samples[-1], 3) if samples else None,
                },
            }

    @staticmethod
    def _percentile(samples: list[float], percentile: float) -> float | None:
        if not samples:
            return None
        index = max(0, math.ceil(len(samples) * percentile) - 1)
        return round(samples[index], 3)
