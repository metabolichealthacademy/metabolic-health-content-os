from datetime import UTC, date, datetime
from hashlib import sha256

import pytest

from content_os.rag.catalog import EvidenceCatalog, EvidenceIngestionError
from content_os.rag.models import EvidenceDocument


def document(version: str, effective_on: date, text: str, **overrides: object) -> EvidenceDocument:
    values = {
        "source_id": "niddk-insulin-resistance",
        "version_id": version,
        "title": "Insulin Resistance and Prediabetes",
        "publisher": "NIDDK",
        "canonical_url": "https://www.niddk.nih.gov/health-information/diabetes/overview/what-is-diabetes/prediabetes-insulin-resistance",
        "published_on": effective_on,
        "effective_on": effective_on,
        "retrieved_at": datetime(2026, 9, 10, tzinfo=UTC),
        "content_sha256": sha256(text.encode()).hexdigest(),
        "text": text,
    }
    values.update(overrides)
    return EvidenceDocument.model_validate(values)


def test_retrieval_selects_version_current_at_as_of_date() -> None:
    catalog = EvidenceCatalog()
    catalog.ingest(
        [
            document("2025-01", date(2025, 1, 1), "Insulin resistance can precede diabetes."),
            document(
                "2026-01",
                date(2026, 1, 1),
                "Insulin resistance and prediabetes are related metabolic conditions.",
                supersedes_version_id="2025-01",
            ),
        ]
    )

    old_hit = catalog.retrieve("insulin diabetes", as_of=date(2025, 6, 1))[0]
    new_hit = catalog.retrieve("insulin prediabetes", as_of=date(2026, 6, 1))[0]

    assert old_hit.document.version_id == "2025-01"
    assert new_hit.document.version_id == "2026-01"
    assert str(new_hit.document.canonical_url).startswith("https://www.niddk.nih.gov/")


def test_retrieval_uses_publication_timestamps_for_same_day_versions() -> None:
    catalog = EvidenceCatalog()
    shared_effective_on = date(2026, 1, 1)
    catalog.ingest(
        [
            document(
                "9",
                shared_effective_on,
                "Earlier same-day version.",
                retrieved_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            ),
            document(
                "10",
                shared_effective_on,
                "Later same-day version.",
                retrieved_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
            ),
        ]
    )

    hit = catalog.retrieve("later", as_of=date(2026, 6, 1))[0]

    assert hit.document.version_id == "10"


def test_retrieval_uses_publication_date_before_retrieval_time_for_same_day_versions() -> None:
    catalog = EvidenceCatalog()
    shared_effective_on = date(2026, 2, 1)
    catalog.ingest(
        [
            document(
                "9",
                shared_effective_on,
                "Earlier publication version.",
                published_on=date(2026, 1, 1),
                retrieved_at=datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
            ),
            document(
                "10",
                shared_effective_on,
                "Later publication version.",
                published_on=date(2026, 2, 1),
                retrieved_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
            ),
        ]
    )

    hit = catalog.retrieve("later publication", as_of=date(2026, 6, 1))[0]

    assert hit.document.version_id == "10"


def test_ingestion_is_allowlisted_hash_verified_and_append_only() -> None:
    catalog = EvidenceCatalog()
    valid = document("2026-01", date(2026, 1, 1), "Prediabetes evidence text.")
    catalog.ingest([valid])

    assert catalog.audit_events[0]["action"] == "evidence_ingested"
    assert catalog.audit_events[0]["content_sha256"] == valid.content_sha256
    assert not hasattr(catalog, "delete")
    with pytest.raises(EvidenceIngestionError, match="Duplicate immutable"):
        catalog.ingest([valid])


def test_ingestion_rejects_unapproved_host_and_changed_content() -> None:
    catalog = EvidenceCatalog()
    with pytest.raises(EvidenceIngestionError, match="not allowlisted"):
        catalog.ingest(
            [
                document(
                    "bad-host",
                    date(2026, 1, 1),
                    "Text",
                    canonical_url="https://example.com/medical-content",
                )
            ]
        )
    with pytest.raises(EvidenceIngestionError, match="hash"):
        catalog.ingest(
            [
                document(
                    "bad-hash",
                    date(2026, 1, 1),
                    "Text",
                    content_sha256="0" * 64,
                )
            ]
        )


def test_catalog_exposes_no_patient_input_or_model_provider_boundary() -> None:
    catalog = EvidenceCatalog()

    assert not hasattr(catalog, "ingest_patient_text")
    assert not hasattr(catalog, "fetch_url")
    assert not hasattr(catalog, "publish")


def test_retrieval_validates_inputs_and_omits_unmatched_or_future_versions() -> None:
    catalog = EvidenceCatalog()
    catalog.ingest([document("2027-01", date(2027, 1, 1), "Future diabetes evidence.")])

    with pytest.raises(ValueError, match="query"):
        catalog.retrieve(" ", as_of=date(2026, 1, 1))
    with pytest.raises(ValueError, match="limit"):
        catalog.retrieve("diabetes", as_of=date(2026, 1, 1), limit=0)
    assert catalog.retrieve("unmatched", as_of=date(2027, 1, 1)) == []
    assert catalog.retrieve("diabetes", as_of=date(2026, 1, 1)) == []


def test_ingestion_rejects_effective_date_before_publication() -> None:
    catalog = EvidenceCatalog()

    with pytest.raises(EvidenceIngestionError, match="effective_on"):
        catalog.ingest(
            [
                document(
                    "invalid-dates",
                    date(2026, 1, 1),
                    "Evidence text.",
                    published_on=date(2026, 2, 1),
                )
            ]
        )
