"""Content, safety, and production-stage data contracts."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

_LEGACY_FINDING_CATEGORIES = {
    "no_supported_claims": "evidence",
    "missing_citations": "evidence",
    "unsupported_source_reference": "evidence",
    "absolute_medical_claim": "editorial",
    "cure_or_guarantee_language": "editorial",
    "editorial_clarity": "editorial",
    "missing_disclaimer": "medical_safety",
    "personalized_medical_instruction": "medical_safety",
    "medication_dose_instruction": "medical_safety",
}


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
            category = _LEGACY_FINDING_CATEGORIES.get(code)
            if category is None:
                raise ValueError(
                    f"Legacy safety finding with unknown code {code!r} must include category; "
                    "valid categories are medical_safety, evidence, or editorial. "
                    "ruleset_version will default to 'legacy' when omitted"
                )
            normalized["category"] = category
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
