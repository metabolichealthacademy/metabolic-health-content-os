"""Evidence structure agent; it does not make scientific-validity judgments."""

from content_os.agents.base import BaseAgent
from content_os.models.evidence import ApprovedClaim, EvidenceOutput, ResearchOutput
from content_os.models.workflow import Workflow, WorkflowStage


class EvidenceAgent(BaseAgent):
    stage = WorkflowStage.EVIDENCE

    def run(self, workflow: Workflow) -> EvidenceOutput:
        research = ResearchOutput.model_validate(self.require_artifact(workflow, "research"))
        known_sources = {source.id for source in research.sources}
        claims = [
            ApprovedClaim(
                text=claim.text,
                source_ids=claim.source_ids,
                structurally_supported=all(
                    source_id in known_sources for source_id in claim.source_ids
                ),
            )
            for claim in research.claims
        ]
        return EvidenceOutput(
            claims=claims,
            limitations=[
                "Citation linkage is structural only; scientific validity requires a later "
                "evidence provider."
            ],
        )
