from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.control_tower.contracts import DatasetContractSchema, build_indicator_contract
from app.control_tower.engine import (
    ExceptionGrant,
    active_exception_codes,
    detect_schema_drift,
    evaluate_contract,
    infer_schema,
    publishable_with_exceptions,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "observation_key": "key-1",
        "region_code": "1100",
        "region_name": "ACEH",
        "indicator_code": "tpt",
        "period": datetime(2025, 8, 1, tzinfo=UTC).date(),
        "value": 5.1,
        "source_value": "5.1",
        "value_status": "observed",
        "unit": "Persen",
        "is_national_aggregate": False,
    }
    row.update(overrides)
    return row


def test_contract_syntax_rejects_unknown_rule_columns() -> None:
    payload = build_indicator_contract("tpt_silver", layer="silver").model_dump()
    payload["uniqueness"] = [{"columns": ["secret_column"], "severity": "critical"}]

    with pytest.raises(ValidationError, match="unknown columns"):
        DatasetContractSchema.model_validate(payload)


def test_critical_contract_failure_blocks_publish_and_samples_are_limited() -> None:
    contract = build_indicator_contract("tpt_silver", layer="silver")
    rows = [_row(observation_key=f"key-{index}") for index in range(8)]
    for row in rows:
        row.pop("region_code")

    report = evaluate_contract(rows, contract, retrieved_at=datetime.now(UTC))
    failed = next(check for check in report.checks if check.code == "column_region_code")

    assert not report.publishable
    assert failed.severity == "critical"
    assert len(failed.safe_sample) == 5


def test_warning_remains_visible_without_blocking_publish() -> None:
    contract = build_indicator_contract("tpt_silver", layer="silver")
    report = evaluate_contract(
        [_row()],
        contract,
        retrieved_at=datetime.now(UTC),
        previous_row_count=100,
    )
    warning = next(check for check in report.checks if check.code == "row_count_change")

    assert not warning.passed
    assert warning.severity == "warning"
    assert report.publishable


def test_expired_exception_no_longer_bypasses_critical_gate() -> None:
    now = datetime.now(UTC)
    contract = build_indicator_contract("tpt_silver", layer="silver")
    report = evaluate_contract([_row(region_code=None)], contract, retrieved_at=now)
    grants = [ExceptionGrant("column_region_code", now - timedelta(seconds=1))]

    codes = active_exception_codes(grants, now=now)

    assert codes == set()
    assert not publishable_with_exceptions(report, codes)


def test_schema_addition_removal_type_and_constraint_changes_are_detected() -> None:
    contract = build_indicator_contract("tpt_silver", layer="silver")
    schema = infer_schema(
        [
            _row(value="not-a-number", extra_column="new"),
            _row(
                observation_key="key-2",
                region_code=None,
                value="not-a-number",
                extra_column="new",
            ),
        ]
    )
    schema.pop("unit")

    changes = detect_schema_drift(contract, schema)
    signatures = {(change.change_type, change.column_name) for change in changes}

    assert ("added", "extra_column") in signatures
    assert ("removed", "unit") in signatures
    assert ("type_changed", "value") in signatures
    assert ("constraint_changed", "region_code") in signatures


def test_retrieval_freshness_uses_retrieval_timestamp() -> None:
    contract = build_indicator_contract("tpt_silver", layer="silver")
    now = datetime.now(UTC)
    report = evaluate_contract(
        [_row(period=datetime(2023, 8, 1, tzinfo=UTC).date())],
        contract,
        retrieved_at=now - timedelta(days=33),
        now=now,
    )
    freshness = next(check for check in report.checks if check.code == "retrieval_freshness")

    assert not freshness.passed
    assert freshness.observed["retrieved_at"] != _row()["period"]
