"""Content, safety, and production-stage data contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class ContentDraft(BaseModel):
    title: str
    audience: str
    body: str
    cited_source_ids: list[str]
    disclaimer: str


class SafetyFinding(BaseModel):
    category: Literal["medical_safety", "evidence", "editorial"]
    severity: Literal["info", "warning", "blocking"]
    code: str
    message: str
    matched_text: str | None = None
    ruleset_version: str


class SafetyReview(BaseModel):
    approved: bool
    findings: list[SafetyFinding]
    ruleset_version: str


class ProductionPackage(BaseModel):
    title: str
    body: str
    source_ids: list[str]
    channels: list[str] = Field(default_factory=lambda: ["review"])
    publish_ready: Literal[False] = False
