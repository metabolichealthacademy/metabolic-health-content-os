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
    severity: Literal["info", "warning", "blocking"]
    code: str
    message: str


class SafetyReview(BaseModel):
    approved: bool
    findings: list[SafetyFinding]


class ProductionPackage(BaseModel):
    title: str
    body: str
    source_ids: list[str]
    channels: list[str] = Field(default_factory=lambda: ["review"])
    publish_ready: Literal[False] = False
