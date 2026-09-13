"""Content, safety, and production-stage data contracts."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="before")
    @classmethod
    def _with_legacy_defaults(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        if "category" not in normalized:
            code = str(normalized.get("code", ""))
            if code in {"no_supported_claims", "missing_citations", "unsupported_source_reference"}:
                normalized["category"] = "evidence"
            elif code in {
                "absolute_medical_claim",
                "cure_or_guarantee_language",
                "editorial_clarity",
            }:
                normalized["category"] = "editorial"
            else:
                normalized["category"] = "medical_safety"
        normalized.setdefault("ruleset_version", "legacy")
        return normalized


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
