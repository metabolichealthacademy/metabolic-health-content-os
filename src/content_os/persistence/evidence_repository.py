"""Transactional persistence for immutable authoritative evidence."""

from datetime import UTC, datetime

from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from content_os.persistence.tables import (
    EvidenceDocumentRow,
    EvidenceDocumentVersionRow,
    EvidenceIngestionReceiptRow,
)
from content_os.rag.catalog import EvidenceIngestionError, validate_evidence_document
from content_os.rag.models import EvidenceDocument, EvidenceIngestionReceipt


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class SqlEvidenceRepository:
    """Read-and-ingest-only repository; versions and receipts are never mutated."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def ingest(self, document: EvidenceDocument) -> EvidenceIngestionReceipt:
        validate_evidence_document(document)
        ingested_at = datetime.now(UTC)

        try:
            with Session(self.engine) as session, session.begin():
                key = (document.source_id, document.version_id)
                if session.get(EvidenceDocumentVersionRow, key) is not None:
                    raise EvidenceIngestionError(f"Duplicate immutable version: {key}")
                self._validate_supersession(session, document)

                if session.get(EvidenceDocumentRow, document.source_id) is None:
                    session.add(
                        EvidenceDocumentRow(
                            source_id=document.source_id,
                            created_at=ingested_at,
                        )
                    )
                    session.flush()

                session.add(self._to_version_row(document, ingested_at))
                session.flush()
                receipt_row = EvidenceIngestionReceiptRow(
                    action="evidence_ingested",
                    source_id=document.source_id,
                    version_id=document.version_id,
                    content_sha256=document.content_sha256,
                    retrieved_at=document.retrieved_at,
                    ingested_at=ingested_at,
                )
                session.add(receipt_row)
                session.flush()
                receipt = self._to_receipt(receipt_row)
        except IntegrityError as exc:
            raise EvidenceIngestionError(
                "Evidence version conflicts with immutable provenance constraints"
            ) from exc

        return receipt

    def get_version(self, source_id: str, version_id: str) -> EvidenceDocument | None:
        with Session(self.engine) as session:
            row = session.get(EvidenceDocumentVersionRow, (source_id, version_id))
            return None if row is None else self._from_version_row(row)

    def list_versions(self, source_id: str) -> list[EvidenceDocument]:
        statement = (
            select(EvidenceDocumentVersionRow)
            .where(EvidenceDocumentVersionRow.source_id == source_id)
            .order_by(
                EvidenceDocumentVersionRow.effective_on,
                EvidenceDocumentVersionRow.published_on,
                EvidenceDocumentVersionRow.retrieved_at,
                EvidenceDocumentVersionRow.version_id,
            )
        )
        with Session(self.engine) as session:
            return [self._from_version_row(row) for row in session.scalars(statement)]

    def list_receipts(
        self, source_id: str | None = None
    ) -> tuple[EvidenceIngestionReceipt, ...]:
        statement = select(EvidenceIngestionReceiptRow).order_by(EvidenceIngestionReceiptRow.id)
        if source_id is not None:
            statement = statement.where(EvidenceIngestionReceiptRow.source_id == source_id)
        with Session(self.engine) as session:
            return tuple(self._to_receipt(row) for row in session.scalars(statement))

    @staticmethod
    def _validate_supersession(session: Session, document: EvidenceDocument) -> None:
        superseded = document.supersedes_version_id
        if superseded is None:
            return
        if superseded == document.version_id:
            raise EvidenceIngestionError("A version cannot supersede itself")
        if session.get(EvidenceDocumentVersionRow, (document.source_id, superseded)) is None:
            raise EvidenceIngestionError(
                "supersedes_version_id must reference an existing version of the same source"
            )

    @staticmethod
    def _to_version_row(
        document: EvidenceDocument, created_at: datetime
    ) -> EvidenceDocumentVersionRow:
        return EvidenceDocumentVersionRow(
            source_id=document.source_id,
            version_id=document.version_id,
            title=document.title,
            publisher=document.publisher,
            canonical_url=str(document.canonical_url),
            published_on=document.published_on,
            effective_on=document.effective_on,
            retrieved_at=document.retrieved_at,
            supersedes_version_id=document.supersedes_version_id,
            content_sha256=document.content_sha256,
            text=document.text,
            created_at=created_at,
        )

    @staticmethod
    def _from_version_row(row: EvidenceDocumentVersionRow) -> EvidenceDocument:
        return EvidenceDocument(
            source_id=row.source_id,
            version_id=row.version_id,
            title=row.title,
            publisher=row.publisher,
            canonical_url=row.canonical_url,
            published_on=row.published_on,
            effective_on=row.effective_on,
            retrieved_at=_as_utc(row.retrieved_at),
            supersedes_version_id=row.supersedes_version_id,
            content_sha256=row.content_sha256,
            text=row.text,
        )

    @staticmethod
    def _to_receipt(row: EvidenceIngestionReceiptRow) -> EvidenceIngestionReceipt:
        return EvidenceIngestionReceipt(
            id=row.id,
            action=row.action,
            source_id=row.source_id,
            version_id=row.version_id,
            content_sha256=row.content_sha256,
            retrieved_at=_as_utc(row.retrieved_at),
            ingested_at=_as_utc(row.ingested_at),
        )
