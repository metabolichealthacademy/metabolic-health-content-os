"""State-machine orchestrator for the five V1 agents."""

from content_os.agents import (
    ContentAgent,
    EvidenceAgent,
    ProductionAgent,
    ResearchAgent,
    SafetyAgent,
)
from content_os.agents.base import BaseAgent
from content_os.models.content import SafetyReview
from content_os.models.workflow import Workflow, WorkflowEvent, WorkflowStage, WorkflowStatus


class InvalidTransitionError(ValueError):
    """Raised when a caller attempts to bypass a workflow gate."""


class Orchestrator:
    def __init__(self, agents: list[BaseAgent] | None = None) -> None:
        configured = agents or [
            ResearchAgent(),
            EvidenceAgent(),
            ContentAgent(),
            SafetyAgent(),
            ProductionAgent(),
        ]
        self.agents = {agent.stage: agent for agent in configured}

    def advance(self, workflow: Workflow) -> Workflow:
        if workflow.status not in {WorkflowStatus.ACTIVE, WorkflowStatus.REVISION_REQUIRED}:
            raise InvalidTransitionError(f"Cannot advance workflow with status {workflow.status}")
        if workflow.stage not in self.agents:
            raise InvalidTransitionError(f"No agent may run at stage {workflow.stage}")

        previous = workflow.stage
        artifact = self.agents[previous].run(workflow)
        workflow.artifacts[previous.value] = artifact.model_dump(mode="json")

        if previous == WorkflowStage.SAFETY:
            review = SafetyReview.model_validate(artifact)
            if not review.approved:
                workflow.stage = WorkflowStage.CONTENT
                workflow.status = WorkflowStatus.REVISION_REQUIRED
                workflow.revision_count += 1
            else:
                workflow.stage = WorkflowStage.PRODUCTION
                workflow.status = WorkflowStatus.ACTIVE
        elif previous == WorkflowStage.PRODUCTION:
            workflow.stage = WorkflowStage.HUMAN_REVIEW
            workflow.status = WorkflowStatus.AWAITING_HUMAN
        else:
            order = {
                WorkflowStage.RESEARCH: WorkflowStage.EVIDENCE,
                WorkflowStage.EVIDENCE: WorkflowStage.CONTENT,
                WorkflowStage.CONTENT: WorkflowStage.SAFETY,
            }
            workflow.stage = order[previous]
            workflow.status = WorkflowStatus.ACTIVE

        workflow.history.append(
            WorkflowEvent(
                action="advance",
                from_stage=previous,
                to_stage=workflow.stage,
                note="Safety revision required"
                if workflow.status == WorkflowStatus.REVISION_REQUIRED
                else None,
            )
        )
        return workflow

    def approve(self, workflow: Workflow, actor_id: str) -> Workflow:
        if (
            workflow.stage != WorkflowStage.HUMAN_REVIEW
            or workflow.status != WorkflowStatus.AWAITING_HUMAN
        ):
            raise InvalidTransitionError("Human approval is only allowed after production")
        previous = workflow.stage
        workflow.stage = WorkflowStage.COMPLETED
        workflow.status = WorkflowStatus.COMPLETED
        workflow.history.append(
            WorkflowEvent(
                action="human_approve",
                from_stage=previous,
                to_stage=workflow.stage,
                actor_id=actor_id,
            )
        )
        return workflow

    def reject(self, workflow: Workflow, reason: str, actor_id: str) -> Workflow:
        if (
            workflow.stage != WorkflowStage.HUMAN_REVIEW
            or workflow.status != WorkflowStatus.AWAITING_HUMAN
        ):
            raise InvalidTransitionError("Human rejection is only allowed after production")
        previous = workflow.stage
        workflow.stage = WorkflowStage.REJECTED
        workflow.status = WorkflowStatus.REJECTED
        workflow.history.append(
            WorkflowEvent(
                action="human_reject",
                from_stage=previous,
                to_stage=workflow.stage,
                note=reason,
                actor_id=actor_id,
            )
        )
        return workflow
