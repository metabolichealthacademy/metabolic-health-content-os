from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from content_os.persistence.database import build_engine, initialize_database
from content_os.persistence.evidence_repository import SqlEvidenceRepository
from content_os.persistence.tables import (
    EvidenceDocumentRow,
    EvidenceDocumentVersionRow,
    EvidenceIngestionReceiptRow,
)
from content_os.rag.catalog import EvidenceCatalog, EvidenceIngestionError
from content_os.rag.models import EvidenceDocument


def document(version: str, effective_on: date, text: str, **overrides: object) -> EvidenceDocument:
    values = {
        "source_id": "niddk-insulin-resistance",
        "version_id": version,
        "title": "Insulin Resistance and Prediabetes",
        "publisher": "NIDDK",
        "canonical_url": "https://www.niddk.nih.gov/health-information/diabetes/prediabetes",
        "published_on": effective_on,
        "effective_on": effective_on,
        "retrieved_at": datetime(2026, 9, 12, tzinfo=UTC),
        "content_sha256": sha256(text.encode()).hexdigest(),
        "text": text,
    }
    values.update(overrides)
    return EvidenceDocument.model_validate(values)


@pytest.fixture
def repository(tmp_path: Path) -> SqlEvidenceRepository:
    engine = build_engine(f"sqlite:///{tmp_path / 'evidence.db'}")
    initialize_database(engine)
    return SqlEvidenceRepository(engine)


def counts(repository: SqlEvidenceRepository) -> tuple[int, int, int]:
    with Session(repository.engine) as session:
        return (
            session.scalar(select(func.count()).select_from(EvidenceDocumentRow)) or 0,
            session.scalar(select(func.count()).select_from(EvidenceDocumentVersionRow)) or 0,
            session.scalar(select(func.count()).select_from(EvidenceIngestionReceiptRow)) or 0,
        )


def test_ingestion_is_atomic_and_survives_a_new_repository_instance(
    repository: SqlEvidenceRepository,
) -> None:
    original = document("2026-01", date(2026, 1, 1), "Prediabetes evidence text.")
    receipt = repository.ingest(original)

    loaded = SqlEvidenceRepository(repository.engine).get_version(
        original.source_id, original.version_id
    )

    assert loaded == original
    assert receipt.action == "evidence_ingested"
    assert receipt.content_sha256 == original.content_sha256
    assert counts(repository) == (1, 1, 1)


def test_failure_after_all_flushes_rolls_back_entire_ingestion(
    repository: SqlEvidenceRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = document("2026-01", date(2026, 1, 1), "Evidence")

    def fail_after_flush(_: EvidenceIngestionReceiptRow) -> None:
        raise RuntimeError("forced post-flush failure")

    monkeypatch.setattr(SqlEvidenceRepository, "_to_receipt", staticmethod(fail_after_flush))

    with pytest.raises(RuntimeError, match="forced post-flush failure"):
        repository.ingest(original)

    assert counts(repository) == (0, 0, 0)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"content_sha256": "0" * 64}, "hash"),
        ({"canonical_url": "https://example.com/evidence"}, "allowlisted"),
    ],
)
def test_invalid_document_rolls_back_every_record(
    repository: SqlEvidenceRepository, overrides: dict[str, object], message: str
) -> None:
    invalid = document("invalid", date(2026, 1, 1), "Evidence", **overrides)

    with pytest.raises(EvidenceIngestionError, match=message):
        repository.ingest(invalid)

    assert counts(repository) == (0, 0, 0)


def test_duplicate_version_is_rejected_without_an_extra_receipt(
    repository: SqlEvidenceRepository,
) -> None:
    original = document("2026-01", date(2026, 1, 1), "Evidence")
    repository.ingest(original)

    with pytest.raises(EvidenceIngestionError, match="Duplicate immutable"):
        repository.ingest(original)

    assert counts(repository) == (1, 1, 1)


def test_supersession_must_reference_an_existing_version_of_the_same_source(
    repository: SqlEvidenceRepository,
) -> None:
    invalid = document(
        "2026-02",
        date(2026, 2, 1),
        "New evidence",
        supersedes_version_id="missing",
    )

    with pytest.raises(EvidenceIngestionError, match="existing version"):
        repository.ingest(invalid)

    assert counts(repository) == (0, 0, 0)


def test_multiple_versions_reload_with_task_5a_as_of_behavior(
    repository: SqlEvidenceRepository,
) -> None:
    old = document("2025-01", date(2025, 1, 1), "Insulin resistance evidence.")
    new = document(
        "2026-01",
        date(2026, 1, 1),
        "Updated insulin resistance evidence.",
        supersedes_version_id="2025-01",
    )
    repository.ingest(old)
    repository.ingest(new)

    catalog = EvidenceCatalog()
    catalog.ingest(SqlEvidenceRepository(repository.engine).list_versions(old.source_id))

    assert catalog.retrieve("insulin", as_of=date(2025, 6, 1))[0].document.version_id == "2025-01"
    assert catalog.retrieve("insulin", as_of=date(2026, 6, 1))[0].document.version_id == "2026-01"
    assert len(repository.list_receipts()) == 2


def test_receipts_restrict_version_deletion_and_repository_has_no_mutation_api(
    repository: SqlEvidenceRepository,
) -> None:
    original = document("2026-01", date(2026, 1, 1), "Evidence")
    repository.ingest(original)

    assert not hasattr(repository, "update_version")
    assert not hasattr(repository, "delete_version")
    assert not hasattr(repository, "update_receipt")
    assert not hasattr(repository, "delete_receipt")
    assert not hasattr(repository, "ingest_patient_text")
    assert not hasattr(repository, "fetch_url")
    assert not hasattr(repository, "publish")
    with pytest.raises(IntegrityError), Session(repository.engine) as session, session.begin():
        session.execute(
            delete(EvidenceDocumentVersionRow).where(
                EvidenceDocumentVersionRow.source_id == original.source_id
            )
        )
