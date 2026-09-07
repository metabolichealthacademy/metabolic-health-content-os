"""Research intake agent; live retrieval is intentionally not connected."""

from content_os.agents.base import BaseAgent
from content_os.models.evidence import ResearchOutput
from content_os.models.workflow import Workflow, WorkflowStage


class ResearchAgent(BaseAgent):
    stage = WorkflowStage.RESEARCH

    def run(self, workflow: Workflow) -> ResearchOutput:
        return ResearchOutput(
            topic=workflow.topic, sources=workflow.sources, claims=workflow.claims
        )
