"""Production packaging agent; publishing remains intentionally disabled."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft, ProductionPackage, SafetyReview
from content_os.models.workflow import Workflow, WorkflowStage

LEGACY_SAFETY_RULESET_VERSION = "1.0.0"
LEGACY_SAFETY_CATEGORY = "medical_safety"


class ProductionAgent(BaseAgent):
    stage = WorkflowStage.PRODUCTION

    def _with_legacy_safety_defaults(self, artifact: dict[str, Any]) -> dict[str, Any]:
        findings = artifact.get("findings")
        if not isinstance(findings, list):
            return artifact

        review_ruleset_version = artifact.get("ruleset_version")
        review_ruleset_is_string = isinstance(review_ruleset_version, str)
        has_review_ruleset_version = (
            isinstance(review_ruleset_version, str) and bool(review_ruleset_version.strip())
        )
        default_ruleset_version = (
            review_ruleset_version.strip()
            if has_review_ruleset_version
            else LEGACY_SAFETY_RULESET_VERSION
        )

        changed = False
        missing_finding_ruleset_version = False
        normalized_findings: list[Any] = []
        for finding in findings:
            if not isinstance(finding, dict):
                normalized_findings.append(finding)
                continue

            normalized_finding = finding
            if "category" not in normalized_finding:
                normalized_finding = {**normalized_finding, "category": LEGACY_SAFETY_CATEGORY}
                changed = True
            if "ruleset_version" not in normalized_finding:
                normalized_finding = {
                    **normalized_finding,
                    "ruleset_version": default_ruleset_version,
                }
                missing_finding_ruleset_version = True
                changed = True
            normalized_findings.append(normalized_finding)

        should_backfill_review_ruleset = (
            not review_ruleset_is_string
            or (not has_review_ruleset_version and missing_finding_ruleset_version)
        )

        if not changed:
            if not should_backfill_review_ruleset:
                return artifact
            return {**artifact, "ruleset_version": default_ruleset_version}

        normalized_artifact = {**artifact, "findings": normalized_findings}
        if should_backfill_review_ruleset:
            normalized_artifact["ruleset_version"] = default_ruleset_version
        return normalized_artifact

    def run(self, workflow: Workflow) -> ProductionPackage:
        safety_artifact = self.require_artifact(workflow, "safety")
        if isinstance(safety_artifact, BaseModel):
            review_mapping = safety_artifact.model_dump(mode="json")
        elif isinstance(safety_artifact, Mapping):
            review_mapping = dict(safety_artifact)
        else:
            review_mapping = dict(safety_artifact)
        findings = review_mapping.get("findings")
        if isinstance(findings, list):
            normalized_findings = []
            for finding in findings:
                if isinstance(finding, BaseModel):
                    normalized_findings.append(finding.model_dump(mode="json"))
                elif isinstance(finding, Mapping):
                    normalized_findings.append(dict(finding))
                else:
                    try:
                        normalized_findings.append(dict(finding))
                    except TypeError:
                        normalized_findings.append(
                            {
                                "severity": getattr(finding, "severity", "warning"),
                                "code": getattr(finding, "code", "legacy_finding"),
                                "message": getattr(
                                    finding,
                                    "message",
                                    f"Legacy finding preserved from {type(finding).__name__}.",
                                ),
                                "matched_text": getattr(finding, "matched_text", None),
                            }
                        )
            review_mapping = {**review_mapping, "findings": normalized_findings}
        review = SafetyReview.model_validate(
            self._with_legacy_safety_defaults(review_mapping)
        )
        if not review.approved:
            raise ValueError("Production requires safety approval")
        draft = ContentDraft.model_validate(self.require_artifact(workflow, "content"))
        return ProductionPackage(
            title=draft.title,
            body=f"{draft.body}\n\n{draft.disclaimer}",
            source_ids=draft.cited_source_ids,
        )
