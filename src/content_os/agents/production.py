"""Production packaging agent; publishing remains intentionally disabled."""

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft, ProductionPackage, SafetyReview
from content_os.models.workflow import Workflow, WorkflowStage


class ProductionAgent(BaseAgent):
    stage = WorkflowStage.PRODUCTION

    def run(self, workflow: Workflow) -> ProductionPackage:
        raw_review = self.require_artifact(workflow, "safety")
        for finding in raw_review.get("findings", []):
            finding.setdefault("category", "medical_safety")
            finding.setdefault("ruleset_version", "legacy")
        raw_review.setdefault("ruleset_version", "legacy")

        review = SafetyReview.model_validate(raw_review)
        if not review.approved:
            raise ValueError("Production requires safety approval")
        draft = ContentDraft.model_validate(self.require_artifact(workflow, "content"))
        return ProductionPackage(
            title=draft.title,
            body=f"{draft.body}\n\n{draft.disclaimer}",
            source_ids=draft.cited_source_ids,
        )
