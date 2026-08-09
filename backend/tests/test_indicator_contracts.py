from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.pipeline.contracts import CONTRACTS
from app.pipeline.normalize import normalize_payload
from app.pipeline.quality import evaluate_quality
from app.pipeline.types import RetrievedPayload

FIXTURE_DIRECTORY = Path(__file__).parents[2] / "tests" / "fixtures" / "bps"

CASES = {
    "tpt": (
        "tpt_august_543_2023_2025_live.json",
        113,
        4,
        "fd602ec5cf5feedb7dc3253a9b6655cb16235531998b13befe4909cc8ae3880e",
    ),
    "tpak": (
        "tpak_august_2396_2023_2025_live.json",
        113,
        4,
        "5a66d272a6d9339a56f1def298f102294e39d69ea8c5cbb1b42374ee26e38792",
    ),
    "poverty_rate": (
        "poverty_march_total_192_2023_2025_live.json",
        113,
        4,
        "0458844b7e34a932eabb5e89eee6c963b2592085566ea8719a7f85752bfa08ec",
    ),
    "grdp_per_capita_current": (
        "grdp_per_capita_current_288_2023_2025_live.json",
        234,
        0,
        "2e2d38ca3ee8841c5b37f56591e929655b2c9f4d518e89c560bf89ca2e7463bb",
    ),
    "grdp_growth_constant_2010": (
        "grdp_growth_constant_2010_291_2023_2025_live.json",
        117,
        0,
        "fd7aebd9ea78940017e6ad93bc2069c1a00391b32aadad6c78343423bc018e84",
    ),
    "hdi": (
        "hdi_new_method_494_2023_2024_live.json",
        78,
        39,
        "5c692d50db5dcdca3fe5d7e0552fe6a0783325eb975abaadf7c8d5bbde8d8f8e",
    ),
}


@pytest.mark.parametrize("indicator", CASES)
def test_live_fixture_satisfies_indicator_contract(indicator: str) -> None:
    filename, raw_count, missing_count, normalized_checksum = CASES[indicator]
    contract = CONTRACTS[indicator]
    body = (FIXTURE_DIRECTORY / filename).read_bytes()
    payload = json.loads(body)
    retrieved = RetrievedPayload(
        endpoint="fixture://bps/list",
        safe_parameters=contract.safe_parameters,
        http_status=200,
        response_headers={"content-type": "application/json"},
        retrieved_at=datetime.now(UTC),
        body_text=body.decode(),
        payload=payload,
        checksum=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        row_count=len(payload["datacontent"]),
    )

    batch = normalize_payload(retrieved, contract)
    report = evaluate_quality(batch, contract)

    assert retrieved.row_count == raw_count
    assert len(batch.observations) == 117
    assert sum(row.value_status == "missing" for row in batch.observations) == missing_count
    assert not batch.quarantined
    assert batch.checksum == normalized_checksum
    assert report.publishable


def test_derived_variable_request_policy_is_explicit() -> None:
    assert CONTRACTS["poverty_rate"].safe_parameters["turvar"] == "434"
    assert "turvar" not in CONTRACTS["grdp_per_capita_current"].safe_parameters
