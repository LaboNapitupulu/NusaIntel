from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class RetrievedPayload:
    endpoint: str
    safe_parameters: dict[str, str]
    http_status: int
    response_headers: dict[str, str]
    retrieved_at: datetime
    body_text: str
    payload: dict[str, Any]
    checksum: str
    byte_count: int
    row_count: int

    @property
    def source_identity(self) -> str:
        parameter_string = "&".join(
            f"{key}={self.safe_parameters[key]}" for key in sorted(self.safe_parameters)
        )
        return f"{self.endpoint}?{parameter_string}"


@dataclass(frozen=True, slots=True)
class NormalizedObservation:
    observation_key: str
    region_code: str
    region_name: str
    indicator_code: str
    period: date
    value: Decimal | None
    source_value: str | None
    value_status: str
    unit: str
    is_national_aggregate: bool


@dataclass(frozen=True, slots=True)
class QuarantinedRow:
    reason_code: str
    source_key: str
    safe_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NormalizedBatch:
    observations: tuple[NormalizedObservation, ...]
    quarantined: tuple[QuarantinedRow, ...]
    checksum: str


@dataclass(frozen=True, slots=True)
class QualityCheck:
    code: str
    severity: str
    passed: bool
    expected: dict[str, Any]
    observed: dict[str, Any]
    safe_sample: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class QualityReport:
    checks: tuple[QualityCheck, ...]

    @property
    def publishable(self) -> bool:
        return all(check.passed or check.severity != "critical" for check in self.checks)


@dataclass(frozen=True, slots=True)
class PipelineOutcome:
    status: str
    run_id: str
    bronze_version_id: str
    silver_version_id: str | None
    gold_version_id: str | None
    raw_observations: int
    normalized_observations: int
    published_observations: int
    quarantined_observations: int
    checksum: str
