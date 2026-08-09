"""Add BPS medallion pipeline storage.

Revision ID: 20260809_0002
Revises: 20260809_0001
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0002"
down_revision: str | None = "20260809_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column("observation_key", sa.String(length=64), nullable=True),
        schema="silver",
    )
    op.add_column(
        "observations",
        sa.Column("source_value", sa.Text(), nullable=True),
        schema="silver",
    )
    op.execute(
        "UPDATE silver.observations "
        "SET observation_key = md5(id::text) "
        "WHERE observation_key IS NULL"
    )
    op.alter_column("observations", "observation_key", nullable=False, schema="silver")
    op.create_unique_constraint(
        "uq_observations_version_key",
        "observations",
        ["dataset_version_id", "observation_key"],
        schema="silver",
    )

    op.create_table(
        "raw_payloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("safe_parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_count", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_raw_payloads_dataset_version_id_dataset_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_payloads")),
        sa.UniqueConstraint("dataset_version_id", name=op.f("uq_raw_payloads_dataset_version_id")),
        schema="bronze",
    )
    op.create_table(
        "quarantine_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("source_key", sa.String(length=512), nullable=False),
        sa.Column("safe_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_quarantine_records_dataset_version_id_dataset_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["ops.pipeline_runs.id"],
            name=op.f("fk_quarantine_records_pipeline_run_id_pipeline_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quarantine_records")),
        sa.UniqueConstraint(
            "dataset_version_id",
            "source_key",
            "reason_code",
            name="uq_quarantine_record",
        ),
        schema="ops",
    )
    op.create_table(
        "regional_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_key", sa.String(length=64), nullable=False),
        sa.Column("region_code", sa.String(length=16), nullable=False),
        sa.Column("indicator_code", sa.String(length=128), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("value_status", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("is_national_aggregate", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_regional_observations_dataset_version_id_dataset_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["indicator_code"],
            ["silver.indicators.code"],
            name=op.f("fk_regional_observations_indicator_code_indicators"),
        ),
        sa.ForeignKeyConstraint(
            ["region_code"],
            ["silver.regions.code"],
            name=op.f("fk_regional_observations_region_code_regions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regional_observations")),
        sa.UniqueConstraint(
            "dataset_version_id",
            "observation_key",
            name="uq_gold_observation_version_key",
        ),
        schema="gold",
    )
    op.create_table(
        "coverage_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_code", sa.String(length=128), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("expected_regions", sa.Integer(), nullable=False),
        sa.Column("observed_regions", sa.Integer(), nullable=False),
        sa.Column("missing_regions", sa.Integer(), nullable=False),
        sa.Column("coverage_percent", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_coverage_summaries_dataset_version_id_dataset_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["indicator_code"],
            ["silver.indicators.code"],
            name=op.f("fk_coverage_summaries_indicator_code_indicators"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coverage_summaries")),
        sa.UniqueConstraint(
            "dataset_version_id", "indicator_code", "period", name="uq_coverage_summary"
        ),
        schema="gold",
    )
    op.execute(
        """
        CREATE VIEW gold.latest_regional_observations AS
        SELECT DISTINCT ON (gro.indicator_code, gro.region_code, gro.period)
            gro.id,
            gro.dataset_version_id,
            gro.observation_key,
            gro.region_code,
            gro.indicator_code,
            gro.period,
            gro.value,
            gro.value_status,
            gro.unit,
            gro.is_national_aggregate,
            gro.created_at
        FROM gold.regional_observations AS gro
        JOIN ops.dataset_versions AS dv ON dv.id = gro.dataset_version_id
        WHERE dv.status = 'published'
        ORDER BY
            gro.indicator_code,
            gro.region_code,
            gro.period,
            dv.processed_at DESC NULLS LAST,
            gro.created_at DESC
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS gold.latest_regional_observations")
    op.drop_table("coverage_summaries", schema="gold")
    op.drop_table("regional_observations", schema="gold")
    op.drop_table("quarantine_records", schema="ops")
    op.drop_table("raw_payloads", schema="bronze")
    op.drop_constraint(
        "uq_observations_version_key", "observations", schema="silver", type_="unique"
    )
    op.drop_column("observations", "source_value", schema="silver")
    op.drop_column("observations", "observation_key", schema="silver")
