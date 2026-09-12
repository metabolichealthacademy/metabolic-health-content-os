"""Persist immutable evidence versions and append-only ingestion receipts."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_documents",
        sa.Column("source_id", sa.String(200), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "evidence_document_versions",
        sa.Column(
            "source_id",
            sa.String(200),
            sa.ForeignKey("evidence_documents.source_id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("version_id", sa.String(200), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("publisher", sa.String(100), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_version_id", sa.String(200)),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id", "supersedes_version_id"],
            ["evidence_document_versions.source_id", "evidence_document_versions.version_id"],
            name="fk_evidence_version_supersedes",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "source_id",
            "version_id",
            "content_sha256",
            name="uq_evidence_version_receipt_target",
        ),
    )
    op.create_index(
        "ix_evidence_document_versions_effective_on",
        "evidence_document_versions",
        ["effective_on"],
    )
    op.create_table(
        "evidence_ingestion_receipts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.Column("version_id", sa.String(200), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id", "version_id", "content_sha256"],
            [
                "evidence_document_versions.source_id",
                "evidence_document_versions.version_id",
                "evidence_document_versions.content_sha256",
            ],
            name="fk_receipt_exact_evidence_version",
            ondelete="RESTRICT",
        ),
    )


def downgrade() -> None:
    op.drop_table("evidence_ingestion_receipts")
    op.drop_index(
        "ix_evidence_document_versions_effective_on",
        table_name="evidence_document_versions",
    )
    op.drop_table("evidence_document_versions")
    op.drop_table("evidence_documents")
