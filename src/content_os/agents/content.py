"""Drafting agent constrained to structurally supported claims."""

from content_os.agents.base import BaseAgent
from content_os.models.content import ContentDraft
from content_os.models.evidence import EvidenceOutput
from content_os.models.workflow import Workflow, WorkflowStage

DISCLAIMER = (
    "Educational information only; not medical advice, diagnosis, or treatment. "
    "Consult a qualified healthcare professional for individual care."
)


class ContentAgent(BaseAgent):
    stage = WorkflowStage.CONTENT

    def run(self, workflow: Workflow) -> ContentDraft:
        evidence = EvidenceOutput.model_validate(self.require_artifact(workflow, "evidence"))
        supported = [claim for claim in evidence.claims if claim.structurally_supported]
        body = "\n".join(f"- {claim.text} [{', '.join(claim.source_ids)}]" for claim in supported)
        return ContentDraft(
            title=workflow.topic,
            audience=workflow.audience,
            body=body,
            cited_source_ids=sorted({item for claim in supported for item in claim.source_ids}),
            disclaimer=DISCLAIMER,
        )
