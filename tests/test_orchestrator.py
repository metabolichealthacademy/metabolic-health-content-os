import pytest

from content_os.models.evidence import ClaimCandidate, SourceCandidate
from content_os.models.workflow import Workflow, WorkflowStage, WorkflowStatus
from content_os.orchestration.orchestrator import InvalidTransitionError, Orchestrator


def valid_workflow() -> Workflow:
    return Workflow(
        topic="Understanding insulin resistance",
        audience="general public",
        sources=[
            SourceCandidate(
                id="nih-1",
                title="Insulin Resistance",
                publisher="NIDDK",
                url="https://www.niddk.nih.gov/health-information/diabetes/overview/what-is-diabetes/prediabetes-insulin-resistance",
            )
        ],
        claims=[
            ClaimCandidate(
                text="Insulin resistance can precede type 2 diabetes.", source_ids=["nih-1"]
            )
        ],
    )


def test_valid_workflow_requires_all_agents_and_human_approval() -> None:
    workflow = valid_workflow()
    orchestrator = Orchestrator()

    for expected_stage in [
        WorkflowStage.EVIDENCE,
        WorkflowStage.CONTENT,
        WorkflowStage.SAFETY,
        WorkflowStage.PRODUCTION,
        WorkflowStage.HUMAN_REVIEW,
    ]:
        orchestrator.advance(workflow)
        assert workflow.stage == expected_stage

    assert workflow.status == WorkflowStatus.AWAITING_HUMAN
    assert workflow.artifacts["production"]["publish_ready"] is False

    orchestrator.approve(workflow, actor_id="reviewer-1")
    assert workflow.stage == WorkflowStage.COMPLETED
    assert workflow.status == WorkflowStatus.COMPLETED


def test_safety_rejection_routes_back_to_content() -> None:
    workflow = Workflow(
        topic="Topic without evidence", audience="general public", sources=[], claims=[]
    )
    orchestrator = Orchestrator()

    for _ in range(4):
        orchestrator.advance(workflow)

    assert workflow.stage == WorkflowStage.CONTENT
    assert workflow.status == WorkflowStatus.REVISION_REQUIRED
    assert workflow.revision_count == 1
    assert workflow.artifacts["safety"]["approved"] is False


def test_human_cannot_approve_early() -> None:
    with pytest.raises(InvalidTransitionError, match="only allowed after production"):
        Orchestrator().approve(valid_workflow(), actor_id="reviewer-1")


def test_completed_workflow_cannot_advance() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.COMPLETED
    workflow.status = WorkflowStatus.COMPLETED

    with pytest.raises(InvalidTransitionError, match="Cannot advance"):
        Orchestrator().advance(workflow)
