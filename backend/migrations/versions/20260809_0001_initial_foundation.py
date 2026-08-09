"""Create Phase 1 foundation schemas and tables.

Revision ID: 20260809_0001
Revises:
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ops")
    op.execute("CREATE SCHEMA IF NOT EXISTS silver")
    op.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    op.execute("CREATE SCHEMA IF NOT EXISTS gold")

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("code", name=op.f("uq_sources_code")),
        schema="ops",
    )
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("layer", sa.String(length=32), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("freshness_sla_seconds", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "freshness_sla_seconds > 0", name=op.f("ck_datasets_freshness_sla_positive")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["ops.sources.id"], name=op.f("fk_datasets_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datasets")),
        sa.UniqueConstraint("source_id", "code", name="uq_datasets_source_code"),
        schema="ops",
    )
    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_identity", sa.String(length=512), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("code_commit", sa.String(length=64), nullable=True),
        sa.Column("source_reference_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_count", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "row_count >= 0", name=op.f("ck_dataset_versions_row_count_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["ops.datasets.id"],
            name=op.f("fk_dataset_versions_dataset_id_datasets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_versions")),
        sa.UniqueConstraint(
            "dataset_id", "source_identity", "checksum", name="uq_dataset_versions_identity"
        ),
        schema="ops",
    )
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("error_category", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_pipeline_runs_dataset_version_id_dataset_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_runs")),
        sa.UniqueConstraint("correlation_id", name=op.f("uq_pipeline_runs_correlation_id")),
        schema="ops",
    )
    op.create_table(
        "data_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("specification", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version > 0", name=op.f("ck_data_contracts_version_positive")),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["ops.datasets.id"], name=op.f("fk_data_contracts_dataset_id_datasets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_contracts")),
        sa.UniqueConstraint("dataset_id", "version", name="uq_data_contracts_dataset_version"),
        schema="ops",
    )
    op.create_table(
        "quality_check_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_code", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expected", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("safe_sample", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_quality_check_results_dataset_version_id_dataset_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["ops.pipeline_runs.id"],
            name=op.f("fk_quality_check_results_pipeline_run_id_pipeline_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_check_results")),
        schema="ops",
    )
    op.create_table(
        "lineage_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upstream_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("downstream_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transformation_version", sa.String(length=128), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "upstream_version_id <> downstream_version_id",
            name=op.f("ck_lineage_edges_versions_differ"),
        ),
        sa.ForeignKeyConstraint(
            ["downstream_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_lineage_edges_downstream_version_id_dataset_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["ops.pipeline_runs.id"], name=op.f("fk_lineage_edges_run_id_pipeline_runs")
        ),
        sa.ForeignKeyConstraint(
            ["upstream_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_lineage_edges_upstream_version_id_dataset_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lineage_edges")),
        sa.UniqueConstraint(
            "upstream_version_id",
            "downstream_version_id",
            "transformation_version",
            name="uq_lineage_edges_versions_transform",
        ),
        schema="ops",
    )
    op.create_table(
        "regions",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("parent_code", sa.String(length=16), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["parent_code"], ["silver.regions.code"], name=op.f("fk_regions_parent_code_regions")
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_regions")),
        schema="silver",
    )
    op.create_table(
        "indicators",
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("favorable_direction", sa.String(length=16), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("reference_period_rule", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "favorable_direction IN ('higher', 'lower', 'context')",
            name=op.f("ck_indicators_valid_favorable_direction"),
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_indicators")),
        schema="silver",
    )
    op.create_table(
        "observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("region_code", sa.String(length=16), nullable=False),
        sa.Column("indicator_code", sa.String(length=128), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("value_status", sa.String(length=32), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("is_national_aggregate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_observations_dataset_version_id_dataset_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["indicator_code"],
            ["silver.indicators.code"],
            name=op.f("fk_observations_indicator_code_indicators"),
        ),
        sa.ForeignKeyConstraint(
            ["region_code"],
            ["silver.regions.code"],
            name=op.f("fk_observations_region_code_regions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_observations")),
        sa.UniqueConstraint(
            "region_code",
            "indicator_code",
            "dataset_version_id",
            "period",
            name="uq_observations_natural_key",
        ),
        schema="silver",
    )


def downgrade() -> None:
    op.drop_table("observations", schema="silver")
    op.drop_table("indicators", schema="silver")
    op.drop_table("regions", schema="silver")
    op.drop_table("lineage_edges", schema="ops")
    op.drop_table("quality_check_results", schema="ops")
    op.drop_table("data_contracts", schema="ops")
    op.drop_table("pipeline_runs", schema="ops")
    op.drop_table("dataset_versions", schema="ops")
    op.drop_table("datasets", schema="ops")
    op.drop_table("sources", schema="ops")
    op.execute("DROP SCHEMA IF EXISTS gold")
    op.execute("DROP SCHEMA IF EXISTS bronze")
    op.execute("DROP SCHEMA IF EXISTS silver")
    op.execute("DROP SCHEMA IF EXISTS ops")
