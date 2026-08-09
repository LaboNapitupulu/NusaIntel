from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.bps.client import BPSClient
from app.bps.errors import BPSError
from app.config import get_settings
from app.pipeline.contracts import CONTRACTS
from app.pipeline.normalize import normalize_payload
from app.pipeline.quality import evaluate_quality


async def _run() -> list[dict[str, Any]]:
    settings = get_settings()
    results: list[dict[str, Any]] = []
    async with BPSClient(settings) as client:
        for contract in CONTRACTS.values():
            started = time.perf_counter()
            try:
                retrieved = await client.fetch(contract)
            except BPSError as error:
                results.append(
                    {
                        "indicator": contract.code,
                        "publishable": False,
                        "error_category": error.category,
                        "duration_seconds": round(time.perf_counter() - started, 3),
                    }
                )
                continue
            batch = normalize_payload(retrieved, contract)
            report = evaluate_quality(batch, contract)
            coverage = {
                str(period.year): sum(
                    row.value_status == "observed"
                    for row in batch.observations
                    if not row.is_national_aggregate and row.period.year == period.year
                )
                for period in contract.periods
            }
            results.append(
                {
                    "indicator": contract.code,
                    "raw_observations": retrieved.row_count,
                    "normalized_observations": len(batch.observations),
                    "observed_provinces": coverage,
                    "missing_observations": sum(
                        row.value_status == "missing" for row in batch.observations
                    ),
                    "invalid_observations": sum(
                        row.value_status == "invalid" for row in batch.observations
                    ),
                    "quarantined_observations": len(batch.quarantined),
                    "publishable": report.publishable,
                    "failed_checks": [check.code for check in report.checks if not check.passed],
                    "checksum": batch.checksum,
                    "duration_seconds": round(time.perf_counter() - started, 3),
                }
            )
    return results


def main() -> None:
    print(json.dumps(asyncio.run(_run()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
