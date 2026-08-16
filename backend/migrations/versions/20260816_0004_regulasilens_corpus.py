"""Add RegulasiLens governed corpus storage.

Revision ID: 20260816_0004
Revises: 20260811_0003
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260816_0004"
down_revision: str | None = "20260811_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS regulations")
    op.create_table(
        "regulation_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_count", sa.BigInteger(), nullable=False),
        sa.Column("body", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_regulation_documents_dataset_version_id_dataset_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regulation_documents")),
        sa.UniqueConstraint(
            "dataset_version_id", name=op.f("uq_regulation_documents_dataset_version_id")
        ),
        schema="bronze",
    )
    op.create_table(
        "documents",
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=128), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("effective_at", sa.Date(), nullable=False),
        sa.Column("status_checked_at", sa.Date(), nullable=False),
        sa.Column("source_page_url", sa.Text(), nullable=False),
        sa.Column("content_url", sa.Text(), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["ops.datasets.id"], name=op.f("fk_documents_dataset_id_datasets")
        ),
        sa.PrimaryKeyConstraint("document_id", name=op.f("pk_documents")),
        sa.UniqueConstraint("dataset_id", name=op.f("uq_documents_dataset_id")),
        schema="regulations",
    )
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manifest_version", sa.String(length=64), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("byte_count", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parser_version", sa.String(length=128), nullable=False),
        sa.Column("parser_status", sa.String(length=32), nullable=False),
        sa.Column("parser_confidence", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("section_count", sa.Integer(), nullable=False),
        sa.Column("source_anchor_coverage", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "source_anchor_coverage >= 0 AND source_anchor_coverage <= 1",
            name=op.f("ck_document_versions_regulation_anchor_coverage_range"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ops.dataset_versions.id"],
            name=op.f("fk_document_versions_dataset_version_id_dataset_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["regulations.documents.document_id"],
            name=op.f("fk_document_versions_document_id_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
        sa.UniqueConstraint(
            "document_id",
            "checksum",
            "parser_version",
            name="uq_regulation_document_parser_version",
        ),
        schema="regulations",
    )
    op.create_table(
        "sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_key", sa.String(length=64), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("heading", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("hierarchy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("source_anchor", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "section_order > 0", name=op.f("ck_sections_regulation_section_order_positive")
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["regulations.document_versions.id"],
            name=op.f("fk_sections_document_version_id_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sections")),
        sa.UniqueConstraint("document_version_id", "section_key", name="uq_regulation_section_key"),
        sa.UniqueConstraint(
            "document_version_id", "section_order", name="uq_regulation_section_order"
        ),
        schema="regulations",
    )
    op.create_table(
        "relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", sa.String(length=128), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("target_document_id", sa.String(length=128), nullable=True),
        sa.Column("target_citation", sa.Text(), nullable=False),
        sa.Column("evidence_url", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["regulations.documents.document_id"],
            name=op.f("fk_relations_source_document_id_documents"),
        ),
        sa.ForeignKeyConstraint(
            ["target_document_id"],
            ["regulations.documents.document_id"],
            name=op.f("fk_relations_target_document_id_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_relations")),
        sa.UniqueConstraint(
            "source_document_id",
            "relation_type",
            "target_citation",
            name="uq_regulation_relation_evidence",
        ),
        schema="regulations",
    )


def downgrade() -> None:
    op.drop_table("relations", schema="regulations")
    op.drop_table("sections", schema="regulations")
    op.drop_table("document_versions", schema="regulations")
    op.drop_table("documents", schema="regulations")
    op.drop_table("regulation_documents", schema="bronze")
    op.execute("DROP SCHEMA IF EXISTS regulations")
