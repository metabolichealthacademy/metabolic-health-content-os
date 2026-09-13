"""Production packaging agent; publishing remains intentionally disabled."""

from typing import Any

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft, ProductionPackage, SafetyReview
from content_os.models.workflow import Workflow, WorkflowStage


class ProductionAgent(BaseAgent):
    stage = WorkflowStage.PRODUCTION

    def _with_legacy_safety_defaults(self, artifact: dict[str, Any]) -> dict[str, Any]:
        findings = artifact.get("findings")
        if not isinstance(findings, list):
            return artifact

        review_ruleset_version = artifact.get("ruleset_version")
        has_review_ruleset_version = isinstance(review_ruleset_version, str)
        default_ruleset_version = review_ruleset_version if has_review_ruleset_version else "1.0.0"

        changed = not has_review_ruleset_version
        normalized_findings: list[Any] = []
        for finding in findings:
            if not isinstance(finding, dict):
                normalized_findings.append(finding)
                continue

            normalized_finding = finding
            if "category" not in normalized_finding:
                normalized_finding = {**normalized_finding, "category": "medical_safety"}
                changed = True
            if "ruleset_version" not in normalized_finding:
                normalized_finding = {
                    **normalized_finding,
                    "ruleset_version": default_ruleset_version,
                }
                changed = True
            normalized_findings.append(normalized_finding)

        if not changed:
            return artifact
        return {
            **artifact,
            "ruleset_version": default_ruleset_version,
            "findings": normalized_findings,
        }

    def run(self, workflow: Workflow) -> ProductionPackage:
        safety_artifact = self.require_artifact(workflow, "safety")
        review = SafetyReview.model_validate(self._with_legacy_safety_defaults(safety_artifact))
        if not review.approved:
            raise ValueError("Production requires safety approval")
        draft = ContentDraft.model_validate(self.require_artifact(workflow, "content"))
        return ProductionPackage(
            title=draft.title,
            body=f"{draft.body}\n\n{draft.disclaimer}",
            source_ids=draft.cited_source_ids,
        )
