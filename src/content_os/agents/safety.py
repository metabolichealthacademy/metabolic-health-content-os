"""Deterministic medical-safety and editorial gate."""

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft, SafetyReview
from content_os.models.evidence import EvidenceOutput
from content_os.models.workflow import Workflow, WorkflowStage
from content_os.safety import MedicalEditorialReviewEngine


class SafetyAgent(BaseAgent):
    stage = WorkflowStage.SAFETY

    def __init__(self, review_engine: MedicalEditorialReviewEngine | None = None) -> None:
        self.review_engine = review_engine or MedicalEditorialReviewEngine()

    def run(self, workflow: Workflow) -> SafetyReview:
        draft = ContentDraft.model_validate(self.require_artifact(workflow, "content"))
        evidence = EvidenceOutput.model_validate(self.require_artifact(workflow, "evidence"))
        return self.review_engine.review(draft, evidence)
