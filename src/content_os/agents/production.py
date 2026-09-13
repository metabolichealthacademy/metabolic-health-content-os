"""Production packaging agent; publishing remains intentionally disabled."""

from collections.abc import Mapping

from pydantic import BaseModel

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft, ProductionPackage, SafetyReview
from content_os.models.workflow import Workflow, WorkflowStage


class ProductionAgent(BaseAgent):
    stage = WorkflowStage.PRODUCTION

    def run(self, workflow: Workflow) -> ProductionPackage:
        raw_review = self.require_artifact(workflow, "safety")
        if isinstance(raw_review, BaseModel):
            review_mapping = raw_review.model_dump(mode="json")
        elif isinstance(raw_review, Mapping):
            review_mapping = dict(raw_review)
        else:
            review_mapping = dict(raw_review)

        normalized_findings = []
        for finding in review_mapping.get("findings", []):
            if isinstance(finding, BaseModel):
                normalized_findings.append(finding.model_dump(mode="json"))
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

        normalized_review = {
            **review_mapping,
            "findings": normalized_findings,
        }
        for finding in normalized_review["findings"]:
            finding.setdefault("category", "medical_safety")
            finding.setdefault("ruleset_version", "legacy")
        normalized_review.setdefault("ruleset_version", "legacy")

        review = SafetyReview.model_validate(normalized_review)
        if not review.approved:
            raise ValueError("Production requires safety approval")
        draft = ContentDraft.model_validate(self.require_artifact(workflow, "content"))
        return ProductionPackage(
            title=draft.title,
            body=f"{draft.body}\n\n{draft.disclaimer}",
            source_ids=draft.cited_source_ids,
        )
