"""Research and evidence-stage data contracts."""

from pydantic import BaseModel, Field, HttpUrl


class SourceCandidate(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: HttpUrl
    publisher: str = Field(min_length=1)


class ClaimCandidate(BaseModel):
    text: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class ResearchOutput(BaseModel):
    topic: str
    sources: list[SourceCandidate]
    claims: list[ClaimCandidate]


class ApprovedClaim(BaseModel):
    text: str
    source_ids: list[str]
    structurally_supported: bool


class EvidenceOutput(BaseModel):
    claims: list[ApprovedClaim]
    limitations: list[str]
