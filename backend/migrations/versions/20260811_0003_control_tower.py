"""Add Control Tower quality governance storage.

Revision ID: 20260811_0003
Revises: 20260809_0002
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260811_0003"
down_revision: str | None = "20260809_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quality_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_code", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_quality_exceptions_quality_exception_expiry_after_creation",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["ops.datasets.id"],
            name=op.f("fk_quality_exceptions_dataset_id_datasets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_exceptions")),
        schema="ops",
    )
    op.add_column(
        "quality_check_results",
        sa.Column("data_contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="ops",
    )
    op.add_column(
        "quality_check_results",
        sa.Column("quality_exception_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="ops",
    )
    op.create_foreign_key(
        op.f("fk_quality_check_results_data_contract_id_data_contracts"),
        "quality_check_results",
        "data_contracts",
        ["data_contract_id"],
        ["id"],
        source_schema="ops",
        referent_schema="ops",
    )
    op.create_foreign_key(
        op.f("fk_quality_check_results_quality_exception_id_quality_exceptions"),
        "quality_check_results",
        "quality_exceptions",
        ["quality_exception_id"],
        ["id"],
        source_schema="ops",
        referent_schema="ops",
    )
    op.create_table(
        "schema_drift_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("column_name", sa.String(length=128), nullable=False),
        sa.Column("expected", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["data_contract_id"],
            ["ops.data_contracts.id"],
            name=op.f("fk_schema_drift_events_data_contract_id_data_contracts"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_schema_drift_events_dataset_version_id_dataset_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schema_drift_events")),
        schema="ops",
    )
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_code", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'ignored-with-reason')",
            name=op.f("ck_incidents_incident_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["ops.datasets.id"], name=op.f("fk_incidents_dataset_id_datasets")
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["ops.pipeline_runs.id"],
            name=op.f("fk_incidents_pipeline_run_id_pipeline_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
        sa.UniqueConstraint("pipeline_run_id", "check_code", name="uq_incident_run_check"),
        schema="ops",
    )


def downgrade() -> None:
    op.drop_table("incidents", schema="ops")
    op.drop_table("schema_drift_events", schema="ops")
    op.drop_constraint(
        op.f("fk_quality_check_results_quality_exception_id_quality_exceptions"),
        "quality_check_results",
        schema="ops",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_quality_check_results_data_contract_id_data_contracts"),
        "quality_check_results",
        schema="ops",
        type_="foreignkey",
    )
    op.drop_column("quality_check_results", "quality_exception_id", schema="ops")
    op.drop_column("quality_check_results", "data_contract_id", schema="ops")
    op.drop_table("quality_exceptions", schema="ops")
