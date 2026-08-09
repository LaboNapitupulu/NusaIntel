from __future__ import annotations

from collections import Counter

from app.pipeline.contracts import IndicatorContract
from app.pipeline.types import NormalizedBatch, QualityCheck, QualityReport


def evaluate_quality(
    batch: NormalizedBatch,
    contract: IndicatorContract,
) -> QualityReport:
    province_rows = [row for row in batch.observations if not row.is_national_aggregate]
    invalid_rows = [row for row in batch.observations if row.value_status == "invalid"]
    keys = [row.observation_key for row in batch.observations]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)

    checks: list[QualityCheck] = [
        QualityCheck(
            code="no_quarantined_rows",
            severity="critical",
            passed=not batch.quarantined,
            expected={"count": 0},
            observed={"count": len(batch.quarantined)},
            safe_sample=tuple(
                {
                    "reason_code": row.reason_code,
                    "source_key": row.source_key,
                }
                for row in batch.quarantined[:5]
            ),
        ),
        QualityCheck(
            code="numeric_values_valid",
            severity="critical",
            passed=not invalid_rows,
            expected={"invalid_count": 0},
            observed={"invalid_count": len(invalid_rows)},
            safe_sample=tuple(
                {
                    "period": row.period.isoformat(),
                    "region_code": row.region_code,
                    "source_value": row.source_value,
                }
                for row in invalid_rows[:5]
            ),
        ),
        QualityCheck(
            code="observation_keys_unique",
            severity="critical",
            passed=not duplicates,
            expected={"duplicate_count": 0},
            observed={"duplicate_count": len(duplicates)},
            safe_sample=tuple({"observation_key": key} for key in duplicates[:5]),
        ),
    ]

    for period in contract.periods:
        rows = [row for row in province_rows if row.period.year == period.year]
        observed = sum(row.value_status == "observed" for row in rows)
        checks.append(
            QualityCheck(
                code=f"coverage_{period.year}",
                severity="critical",
                passed=observed >= period.minimum_observed_provinces,
                expected={
                    "minimum_observed_provinces": period.minimum_observed_provinces,
                    "contract_provinces": len(contract.regions),
                },
                observed={"observed_provinces": observed},
            )
        )

    return QualityReport(checks=tuple(checks))
