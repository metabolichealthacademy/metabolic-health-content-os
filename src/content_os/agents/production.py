"""Production packaging agent; publishing remains intentionally disabled."""

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft, ProductionPackage, SafetyReview
from content_os.models.workflow import Workflow, WorkflowStage

_LEGACY_FINDING_CATEGORIES = {
    "no_supported_claims": "evidence",
    "missing_citations": "evidence",
    "unsupported_source_reference": "evidence",
    "missing_disclaimer": "medical_safety",
    "personalized_medical_instruction": "medical_safety",
    "medication_dose_instruction": "medical_safety",
    "absolute_medical_claim": "editorial",
    "cure_or_guarantee_language": "editorial",
    "editorial_clarity": "editorial",
}


def _load_safety_review(artifact: object) -> SafetyReview:
    if not isinstance(artifact, dict):
        return SafetyReview.model_validate(artifact)

    review = dict(artifact)
    findings = review.get("findings")
    if not isinstance(findings, list):
        return SafetyReview.model_validate(review)

    if not any(_is_missing_safety_metadata(finding) for finding in findings):
        return SafetyReview.model_validate(review)

    if not all(
        _is_legacy_safety_finding(finding) or not _is_missing_safety_metadata(finding)
        for finding in findings
    ):
        return SafetyReview.model_validate(review)

    if "ruleset_version" not in review:
        review["ruleset_version"] = "legacy"
    ruleset_version = review["ruleset_version"]
    review["findings"] = [
        (
            _load_safety_finding(finding, ruleset_version)
            if _is_legacy_safety_finding(finding)
            else finding
        )
        for finding in findings
    ]
    return SafetyReview.model_validate(review)


def _is_missing_safety_metadata(artifact: object) -> bool:
    return isinstance(artifact, dict) and (
        "category" not in artifact and "ruleset_version" not in artifact
    )


def _is_legacy_safety_finding(artifact: object) -> bool:
    return (
        isinstance(artifact, dict)
        and "category" not in artifact
        and "ruleset_version" not in artifact
        and artifact.get("code") in _LEGACY_FINDING_CATEGORIES
    )


def _load_safety_finding(artifact: object, ruleset_version: str) -> object:
    if not isinstance(artifact, dict):
        return artifact

    finding = dict(artifact)
    category = finding.get("category")
    if category is None:
        inferred = _LEGACY_FINDING_CATEGORIES.get(finding.get("code"))
        if inferred is not None:
            finding["category"] = inferred
    finding.setdefault("ruleset_version", ruleset_version)
    return finding


class ProductionAgent(BaseAgent):
    stage = WorkflowStage.PRODUCTION

    def run(self, workflow: Workflow) -> ProductionPackage:
        review = _load_safety_review(self.require_artifact(workflow, "safety"))
        if not review.approved:
            raise ValueError("Production requires safety approval")
        draft = ContentDraft.model_validate(self.require_artifact(workflow, "content"))
        return ProductionPackage(
            title=draft.title,
            body=f"{draft.body}\n\n{draft.disclaimer}",
            source_ids=draft.cited_source_ids,
        )
