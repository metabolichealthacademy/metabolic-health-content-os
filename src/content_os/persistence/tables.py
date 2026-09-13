"""Relational database tables."""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class WorkflowRow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic: Mapped[str] = mapped_column(String(300))
    audience: Mapped[str] = mapped_column(String(100))
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    stage: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    artifacts: Mapped[dict[str, Any]] = mapped_column(JSON)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    events: Mapped[list["WorkflowEventRow"]] = relationship(
        back_populates="workflow", order_by="WorkflowEventRow.sequence"
    )


class WorkflowEventRow(Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint("workflow_id", "sequence", name="uq_workflow_event_sequence"),
        Index("ix_workflow_events_workflow_timestamp", "workflow_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflows.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[str | None] = mapped_column(String(128))
    workflow: Mapped[WorkflowRow] = relationship(back_populates="events")


class EvidenceDocumentRow(Base):
    """Stable identity shared by every immutable version of a source."""

    __tablename__ = "evidence_documents"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceDocumentVersionRow(Base):
    """Immutable evidence content and provenance for one source version."""

    __tablename__ = "evidence_document_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "supersedes_version_id"],
            ["evidence_document_versions.source_id", "evidence_document_versions.version_id"],
            name="fk_evidence_version_supersedes",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "source_id",
            "version_id",
            "content_sha256",
            name="uq_evidence_version_receipt_target",
        ),
    )

    source_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("evidence_documents.source_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    version_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    publisher: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    published_on: Mapped[date] = mapped_column(Date, nullable=False)
    effective_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_version_id: Mapped[str | None] = mapped_column(String(200))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceIngestionReceiptRow(Base):
    """Append-only record of a successful evidence-version ingestion."""

    __tablename__ = "evidence_ingestion_receipts"
    __table_args__ = (
        ForeignKeyConstraint(
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)
    version_id: Mapped[str] = mapped_column(String(200), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
