"""Validated contracts for versioned authoritative evidence."""

from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EvidenceDocument(BaseModel):
    """One immutable, source-controlled version of an authoritative document."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    canonical_url: HttpUrl
    published_on: date
    effective_on: date
    retrieved_at: datetime
    supersedes_version_id: str | None = None
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str = Field(min_length=1)

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        return value.astimezone(UTC)


class RetrievalHit(BaseModel):
    """A retrieval result that always carries citation and version provenance."""

    document: EvidenceDocument
    score: int = Field(ge=1)
    matched_terms: list[str] = Field(min_length=1)
