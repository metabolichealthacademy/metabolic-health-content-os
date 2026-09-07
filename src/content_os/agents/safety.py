"""Deterministic minimum safety gate."""

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft, SafetyFinding, SafetyReview
from content_os.models.workflow import Workflow, WorkflowStage


class SafetyAgent(BaseAgent):
    stage = WorkflowStage.SAFETY

    def run(self, workflow: Workflow) -> SafetyReview:
        draft = ContentDraft.model_validate(self.require_artifact(workflow, "content"))
        findings: list[SafetyFinding] = []
        if not draft.body.strip():
            findings.append(
                SafetyFinding(
                    severity="blocking",
                    code="no_supported_claims",
                    message="Draft has no structurally supported claims.",
                )
            )
        if not draft.cited_source_ids:
            findings.append(
                SafetyFinding(
                    severity="blocking",
                    code="missing_citations",
                    message="Draft must cite at least one supplied source.",
                )
            )
        if "not medical advice" not in draft.disclaimer.lower():
            findings.append(
                SafetyFinding(
                    severity="blocking",
                    code="missing_disclaimer",
                    message="Educational medical disclaimer is required.",
                )
            )
        return SafetyReview(
            approved=not any(item.severity == "blocking" for item in findings),
            findings=findings,
        )
