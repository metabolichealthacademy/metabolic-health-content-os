"""Allowlisted ingestion and deterministic, version-aware lexical retrieval."""

from collections.abc import Iterable
from datetime import UTC, date, datetime
from hashlib import sha256
from urllib.parse import urlparse

from content_os.rag.models import EvidenceDocument, RetrievalHit

AUTHORIZED_SOURCES = {"NIDDK": {"www.niddk.nih.gov"}}


class EvidenceIngestionError(ValueError):
    """Raised when a document fails provenance or integrity validation."""


class EvidenceCatalog:
    """Immutable-version catalog used before vector storage or live fetching exists.

    Input is restricted to repository-controlled documents. There is deliberately no
    patient-text, arbitrary upload, URL-fetch, mutation, deletion, or publishing API.
    """

    def __init__(self) -> None:
        self._documents: dict[tuple[str, str], EvidenceDocument] = {}
        self._audit: list[dict[str, str]] = []

    @property
    def audit_events(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(event) for event in self._audit)

    def ingest(self, documents: Iterable[EvidenceDocument]) -> None:
        for document in documents:
            self._validate(document)
            key = (document.source_id, document.version_id)
            if key in self._documents:
                raise EvidenceIngestionError(f"Duplicate immutable version: {key}")
            self._documents[key] = document.model_copy(deep=True)
            self._audit.append(
                {
                    "action": "evidence_ingested",
                    "source_id": document.source_id,
                    "version_id": document.version_id,
                    "content_sha256": document.content_sha256,
                    "retrieved_at": document.retrieved_at.isoformat(),
                }
            )

    def retrieve(self, query: str, *, as_of: date, limit: int = 5) -> list[RetrievalHit]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if limit < 1:
            raise ValueError("limit must be at least 1")

        current = self._current_versions(as_of)
        terms = sorted(set(query.casefold().split()))
        hits: list[RetrievalHit] = []
        for document in current:
            haystack = f"{document.title} {document.text}".casefold()
            matched = [term for term in terms if term in haystack]
            if matched:
                hits.append(
                    RetrievalHit(
                        document=document,
                        score=len(matched),
                        matched_terms=matched,
                    )
                )
        return sorted(
            hits,
            key=lambda hit: (
                -hit.score,
                -hit.document.effective_on.toordinal(),
                hit.document.source_id,
            ),
        )[:limit]

    def _current_versions(self, as_of: date) -> list[EvidenceDocument]:
        eligible = [item for item in self._documents.values() if item.effective_on <= as_of]
        latest: dict[str, EvidenceDocument] = {}
        for item in eligible:
            previous = latest.get(item.source_id)
            if previous is None or self._is_newer_version(item, previous):
                latest[item.source_id] = item
        return list(latest.values())

    @staticmethod
    def _is_newer_version(candidate: EvidenceDocument, current: EvidenceDocument) -> bool:
        candidate_key = (
            candidate.effective_on,
            candidate.published_on or date.min,
            candidate.retrieved_at or datetime.min.replace(tzinfo=UTC),
            candidate.version_id,
        )
        current_key = (
            current.effective_on,
            current.published_on or date.min,
            current.retrieved_at or datetime.min.replace(tzinfo=UTC),
            current.version_id,
        )
        return candidate_key > current_key

    @staticmethod
    def _validate(document: EvidenceDocument) -> None:
        allowed_hosts = AUTHORIZED_SOURCES.get(document.publisher)
        host = (urlparse(str(document.canonical_url)).hostname or "").casefold()
        if allowed_hosts is None or host not in allowed_hosts:
            raise EvidenceIngestionError("Publisher and canonical URL are not allowlisted")
        digest = sha256(document.text.encode()).hexdigest()
        if digest != document.content_sha256:
            raise EvidenceIngestionError("Content hash does not match document text")
        if document.effective_on < document.published_on:
            raise EvidenceIngestionError("effective_on cannot precede published_on")
