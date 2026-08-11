from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.control_tower.contracts import ColumnRule, DatasetContractSchema
from app.pipeline.types import QualityCheck, QualityReport

SAFE_SAMPLE_LIMIT = 5
SAFE_VALUE_LENGTH = 160


@dataclass(frozen=True, slots=True)
class SchemaChange:
    change_type: str
    column_name: str
    expected: dict[str, Any] | None
    observed: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ExceptionGrant:
    check_code: str
    expires_at: datetime
    active: bool = True


def _record(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if is_dataclass(row) and not isinstance(row, type):
        return asdict(row)
    raise TypeError("quality rows must be mappings or dataclass instances")


def _safe_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    rendered = value.isoformat() if isinstance(value, (date, datetime)) else str(value)
    return rendered[:SAFE_VALUE_LENGTH]


def sanitize_samples(
    rows: Sequence[dict[str, Any]], columns: Sequence[str]
) -> tuple[dict[str, Any], ...]:
    safe_columns = tuple(columns[:8])
    return tuple(
        {column: _safe_value(row.get(column)) for column in safe_columns}
        for row in rows[:SAFE_SAMPLE_LIMIT]
    )


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, (float, Decimal)):
        return "number"
    if isinstance(value, datetime):
        return "datetime"
    if isinstance(value, date):
        return "date"
    return "string"


def infer_schema(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not rows:
        return {}
    columns = sorted({key for row in rows for key in row})
    result: dict[str, dict[str, Any]] = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        non_null = [value for value in values if value is not None]
        inferred = sorted({_type_name(value) for value in non_null})
        result[column] = {
            "type": inferred[0] if len(inferred) == 1 else "mixed",
            "nullable": any(value is None for value in values),
        }
    return result


def detect_schema_drift(
    contract: DatasetContractSchema, observed_schema: Mapping[str, Mapping[str, Any]]
) -> tuple[SchemaChange, ...]:
    expected = {column.name: column for column in contract.columns}
    changes: list[SchemaChange] = []
    for name, rule in expected.items():
        observed = observed_schema.get(name)
        if observed is None:
            changes.append(SchemaChange("removed", name, rule.model_dump(mode="json"), None))
            continue
        if observed.get("type") != rule.type:
            changes.append(
                SchemaChange(
                    "type_changed", name, {"type": rule.type}, {"type": observed.get("type")}
                )
            )
        if bool(observed.get("nullable")) and not rule.nullable:
            changes.append(
                SchemaChange(
                    "constraint_changed",
                    name,
                    {"nullable": False},
                    {"nullable": True},
                )
            )
    for name, observed in observed_schema.items():
        if name not in expected:
            changes.append(SchemaChange("added", name, None, dict(observed)))
    return tuple(changes)


def _column_check(rows: Sequence[dict[str, Any]], rule: ColumnRule) -> QualityCheck:
    missing = [row for row in rows if rule.name not in row]
    nulls = [row for row in rows if row.get(rule.name) is None]
    wrong_type = [
        row
        for row in rows
        if row.get(rule.name) is not None and _type_name(row[rule.name]) != rule.type
    ]
    failed = missing or (nulls if not rule.nullable else []) or wrong_type
    return QualityCheck(
        code=f"column_{rule.name}",
        severity="critical",
        passed=not failed,
        expected={"type": rule.type, "nullable": rule.nullable},
        observed={
            "missing": len(missing),
            "null": len(nulls),
            "wrong_type": len(wrong_type),
        },
        safe_sample=sanitize_samples(failed, ["observation_key", rule.name]),
    )


def evaluate_contract(
    raw_rows: Sequence[Any],
    contract: DatasetContractSchema,
    *,
    retrieved_at: datetime,
    previous_row_count: int | None = None,
    now: datetime | None = None,
) -> QualityReport:
    rows = [_record(row) for row in raw_rows]
    checks = [_column_check(rows, column) for column in contract.columns]

    for index, uniqueness_rule in enumerate(contract.uniqueness):
        keys = [tuple(row.get(column) for column in uniqueness_rule.columns) for row in rows]
        duplicates = {key for key, count in Counter(keys).items() if count > 1}
        duplicate_rows = [row for row, key in zip(rows, keys, strict=True) if key in duplicates]
        checks.append(
            QualityCheck(
                code=f"unique_{index + 1}_{'_'.join(uniqueness_rule.columns)}",
                severity=uniqueness_rule.severity,
                passed=not duplicate_rows,
                expected={"duplicate_rows": 0, "columns": uniqueness_rule.columns},
                observed={"duplicate_rows": len(duplicate_rows)},
                safe_sample=sanitize_samples(duplicate_rows, uniqueness_rule.columns),
            )
        )

    for value_rule in contract.values:
        invalid_value_rows: list[dict[str, Any]] = []
        for row in rows:
            value = row.get(value_rule.column)
            if value is None:
                continue
            outside_bounds = (
                value_rule.minimum is not None and float(value) < value_rule.minimum
            ) or (value_rule.maximum is not None and float(value) > value_rule.maximum)
            outside_values = (
                value_rule.accepted_values is not None and value not in value_rule.accepted_values
            )
            if outside_bounds or outside_values:
                invalid_value_rows.append(row)
        checks.append(
            QualityCheck(
                code=f"value_{value_rule.column}",
                severity=value_rule.severity,
                passed=not invalid_value_rows,
                expected={
                    "minimum": value_rule.minimum,
                    "maximum": value_rule.maximum,
                    "accepted_values": value_rule.accepted_values,
                },
                observed={"failing_rows": len(invalid_value_rows)},
                safe_sample=sanitize_samples(
                    invalid_value_rows, ["observation_key", value_rule.column]
                ),
            )
        )

    for custom_rule in contract.custom_checks:
        if custom_rule.operator == "non_null_ratio_gte":
            non_null = sum(row.get(custom_rule.column or "") is not None for row in rows)
            observed_value = non_null / len(rows) if rows else 0.0
            passed = observed_value >= custom_rule.threshold
        elif custom_rule.operator == "row_count_gte":
            observed_value = float(len(rows))
            passed = observed_value >= custom_rule.threshold
        else:
            observed_value = float(len(rows))
            passed = observed_value <= custom_rule.threshold
        checks.append(
            QualityCheck(
                code=custom_rule.code,
                severity=custom_rule.severity,
                passed=passed,
                expected={
                    "operator": custom_rule.operator,
                    "threshold": custom_rule.threshold,
                },
                observed={"value": observed_value},
            )
        )

    active_now = now or datetime.now(UTC)
    age_seconds = max(0.0, (active_now - retrieved_at).total_seconds())
    checks.append(
        QualityCheck(
            code="retrieval_freshness",
            severity=contract.freshness.severity,
            passed=age_seconds <= contract.freshness.retrieval_max_age_seconds,
            expected={"maximum_age_seconds": contract.freshness.retrieval_max_age_seconds},
            observed={
                "age_seconds": age_seconds,
                "retrieved_at": retrieved_at.isoformat(),
                "checked_at": active_now.isoformat(),
            },
        )
    )

    if previous_row_count is not None:
        denominator = max(previous_row_count, 1)
        change = abs(len(rows) - previous_row_count) * 100 / denominator
        checks.append(
            QualityCheck(
                code="row_count_change",
                severity=contract.row_count.severity,
                passed=change <= contract.row_count.maximum_change_percent,
                expected={"maximum_change_percent": contract.row_count.maximum_change_percent},
                observed={
                    "previous_row_count": previous_row_count,
                    "current_row_count": len(rows),
                    "change_percent": change,
                },
            )
        )

    return QualityReport(checks=tuple(checks))


def publishable_with_exceptions(report: QualityReport, active_exception_codes: set[str]) -> bool:
    return all(
        check.passed or check.severity != "critical" or check.code in active_exception_codes
        for check in report.checks
    )


def active_exception_codes(
    grants: Sequence[ExceptionGrant], *, now: datetime | None = None
) -> set[str]:
    active_now = now or datetime.now(UTC)
    return {grant.check_code for grant in grants if grant.active and grant.expires_at > active_now}
