from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.pipeline.contracts import TPT_CONTRACT
from app.pipeline.normalize import normalize_payload
from app.pipeline.quality import evaluate_quality
from app.pipeline.types import RetrievedPayload

FIXTURE_PATH = (
    Path(__file__).parents[2] / "tests" / "fixtures" / "bps" / "tpt_august_543_2023_2025_live.json"
)


def _fixture_payload(payload: dict[str, Any] | None = None) -> RetrievedPayload:
    if payload is None:
        body = FIXTURE_PATH.read_bytes()
        payload = json.loads(body)
    else:
        body = json.dumps(payload, ensure_ascii=False).encode()
    return RetrievedPayload(
        endpoint="fixture://bps/list",
        safe_parameters=TPT_CONTRACT.safe_parameters,
        http_status=200,
        response_headers={"content-type": "application/json"},
        retrieved_at=datetime.now(UTC),
        body_text=body.decode(),
        payload=payload,
        checksum=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        row_count=len(payload["datacontent"]),
    )


def _raw_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_bytes())


def test_normalization_is_deterministic_and_preserves_missing_values() -> None:
    retrieved = _fixture_payload()

    first = normalize_payload(retrieved, TPT_CONTRACT)
    second = normalize_payload(retrieved, TPT_CONTRACT)
    report = evaluate_quality(first, TPT_CONTRACT)

    assert first == second
    assert first.checksum == second.checksum
    assert len(first.observations) == 117
    assert sum(row.value_status == "observed" for row in first.observations) == 113
    assert sum(row.value_status == "missing" for row in first.observations) == 4
    assert not first.quarantined
    assert report.publishable


def test_invalid_numeric_value_is_not_coerced_to_zero_and_blocks_publish() -> None:
    payload = copy.deepcopy(_raw_payload())
    payload["datacontent"]["11005430123190"] = "not-a-number"

    batch = normalize_payload(_fixture_payload(payload), TPT_CONTRACT)
    report = evaluate_quality(batch, TPT_CONTRACT)
    aceh_2023 = next(
        row for row in batch.observations if row.region_code == "1100" and row.period.year == 2023
    )

    assert aceh_2023.value is None
    assert aceh_2023.source_value == "not-a-number"
    assert aceh_2023.value_status == "invalid"
    assert not report.publishable


def test_unknown_region_is_quarantined_and_blocks_publish() -> None:
    payload = copy.deepcopy(_raw_payload())
    payload["vervar"].append({"val": 9800, "label": "WILAYAH UJI"})
    payload["datacontent"]["98005430125190"] = 1.23

    batch = normalize_payload(_fixture_payload(payload), TPT_CONTRACT)
    report = evaluate_quality(batch, TPT_CONTRACT)

    assert len(batch.quarantined) == 1
    assert batch.quarantined[0].reason_code == "unknown_region"
    assert not report.publishable


def test_coverage_below_contract_blocks_publish() -> None:
    payload = copy.deepcopy(_raw_payload())
    del payload["datacontent"]["11005430125190"]

    batch = normalize_payload(_fixture_payload(payload), TPT_CONTRACT)
    report = evaluate_quality(batch, TPT_CONTRACT)
    coverage_2025 = next(check for check in report.checks if check.code == "coverage_2025")

    assert not coverage_2025.passed
    assert not report.publishable
