from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = {"schema": "ops"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    attribution: Mapped[str] = mapped_column(Text, nullable=False)


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("source_id", "code", name="uq_datasets_source_code"),
        CheckConstraint("freshness_sla_seconds > 0", name="freshness_sla_positive"),
        {"schema": "ops"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.sources.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    layer: Mapped[str] = mapped_column(String(32), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    freshness_sla_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class DatasetVersion(TimestampMixin, Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "source_identity", "checksum", name="uq_dataset_versions_identity"
        ),
        CheckConstraint("row_count >= 0", name="row_count_non_negative"),
        {"schema": "ops"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.datasets.id"), nullable=False
    )
    source_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    code_commit: Mapped[str | None] = mapped_column(String(64))
    source_reference_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class PipelineRun(TimestampMixin, Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = {"schema": "ops"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id")
    )
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(128))


class DataContract(TimestampMixin, Base):
    __tablename__ = "data_contracts"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_data_contracts_dataset_version"),
        CheckConstraint("version > 0", name="version_positive"),
        {"schema": "ops"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.datasets.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    specification: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QualityCheckResult(TimestampMixin, Base):
    __tablename__ = "quality_check_results"
    __table_args__ = {"schema": "ops"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.pipeline_runs.id"), nullable=False
    )
    data_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.data_contracts.id")
    )
    quality_exception_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.quality_exceptions.id")
    )
    check_code: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    expected: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    observed: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    safe_sample: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)


class QualityException(TimestampMixin, Base):
    __tablename__ = "quality_exceptions"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="quality_exception_expiry_after_creation"),
        {"schema": "ops"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.datasets.id"), nullable=False
    )
    check_code: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class SchemaDriftEvent(TimestampMixin, Base):
    __tablename__ = "schema_drift_events"
    __table_args__ = {"schema": "ops"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    data_contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.data_contracts.id"), nullable=False
    )
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    column_name: Mapped[str] = mapped_column(String(128), nullable=False)
    expected: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    observed: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'ignored-with-reason')",
            name="incident_valid_status",
        ),
        UniqueConstraint("pipeline_run_id", "check_code", name="uq_incident_run_check"),
        {"schema": "ops"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.datasets.id"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.pipeline_runs.id"), nullable=False
    )
    check_code: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LineageEdge(TimestampMixin, Base):
    __tablename__ = "lineage_edges"
    __table_args__ = (
        CheckConstraint("upstream_version_id <> downstream_version_id", name="versions_differ"),
        UniqueConstraint(
            "upstream_version_id",
            "downstream_version_id",
            "transformation_version",
            name="uq_lineage_edges_versions_transform",
        ),
        {"schema": "ops"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upstream_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    downstream_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    transformation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.pipeline_runs.id"), nullable=False
    )


class Region(TimestampMixin, Base):
    __tablename__ = "regions"
    __table_args__ = {"schema": "silver"}

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(16), ForeignKey("silver.regions.code"))
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)


class Indicator(TimestampMixin, Base):
    __tablename__ = "indicators"
    __table_args__ = (
        CheckConstraint(
            "favorable_direction IN ('higher', 'lower', 'context')",
            name="valid_favorable_direction",
        ),
        {"schema": "silver"},
    )

    code: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    favorable_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    reference_period_rule: Mapped[str] = mapped_column(Text, nullable=False)


class Observation(TimestampMixin, Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint(
            "region_code",
            "indicator_code",
            "dataset_version_id",
            "period",
            name="uq_observations_natural_key",
        ),
        UniqueConstraint(
            "dataset_version_id",
            "observation_key",
            name="uq_observations_version_key",
        ),
        {"schema": "silver"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("silver.regions.code"), nullable=False
    )
    indicator_code: Mapped[str] = mapped_column(
        String(128), ForeignKey("silver.indicators.code"), nullable=False
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    observation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    source_value: Mapped[str | None] = mapped_column(Text)
    value_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_note: Mapped[str | None] = mapped_column(Text)
    is_national_aggregate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )


class RawPayload(TimestampMixin, Base):
    __tablename__ = "raw_payloads"
    __table_args__ = {"schema": "bronze"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ops.dataset_versions.id"),
        unique=True,
        nullable=False,
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    safe_parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response_headers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_count: Mapped[int] = mapped_column(BigInteger, nullable=False)


class QuarantineRecord(TimestampMixin, Base):
    __tablename__ = "quarantine_records"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id", "source_key", "reason_code", name="uq_quarantine_record"
        ),
        {"schema": "ops"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.pipeline_runs.id"), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    source_key: Mapped[str] = mapped_column(String(512), nullable=False)
    safe_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class GoldRegionalObservation(TimestampMixin, Base):
    __tablename__ = "regional_observations"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id", "observation_key", name="uq_gold_observation_version_key"
        ),
        {"schema": "gold"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    observation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    region_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("silver.regions.code"), nullable=False
    )
    indicator_code: Mapped[str] = mapped_column(
        String(128), ForeignKey("silver.indicators.code"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    value_status: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    is_national_aggregate: Mapped[bool] = mapped_column(Boolean, nullable=False)


class CoverageSummary(TimestampMixin, Base):
    __tablename__ = "coverage_summaries"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id", "indicator_code", "period", name="uq_coverage_summary"
        ),
        {"schema": "gold"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ops.dataset_versions.id"), nullable=False
    )
    indicator_code: Mapped[str] = mapped_column(
        String(128), ForeignKey("silver.indicators.code"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    expected_regions: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_regions: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_regions: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
