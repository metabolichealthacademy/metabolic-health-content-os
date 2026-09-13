import pytest

from content_os.models.content import ContentDraft, SafetyReview
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


def test_revision_required_workflow_can_be_human_rejected() -> None:
    workflow = Workflow(
        topic="Topic without evidence", audience="general public", sources=[], claims=[]
    )
    orchestrator = Orchestrator()

    for _ in range(4):
        orchestrator.advance(workflow)

    assert workflow.stage == WorkflowStage.CONTENT
    assert workflow.status == WorkflowStatus.REVISION_REQUIRED
    orchestrator.reject(workflow, reason="Unable to support claims safely", actor_id="reviewer-1")

    assert workflow.stage == WorkflowStage.REJECTED
    assert workflow.status == WorkflowStatus.REJECTED
    assert workflow.history[-1].action == "human_reject"
    assert workflow.history[-1].note == "Unable to support claims safely"
    assert workflow.history[-1].actor_id == "reviewer-1"


def test_human_cannot_approve_early() -> None:
    with pytest.raises(InvalidTransitionError, match="only allowed after production"):
        Orchestrator().approve(valid_workflow(), actor_id="reviewer-1")


def test_human_cannot_reject_before_production_or_revision() -> None:
    with pytest.raises(InvalidTransitionError, match="only allowed after production"):
        Orchestrator().reject(valid_workflow(), reason="Not ready", actor_id="reviewer-1")


def test_human_cannot_reject_from_unsupported_revision_state() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.SAFETY
    workflow.status = WorkflowStatus.REVISION_REQUIRED

    with pytest.raises(InvalidTransitionError, match="only allowed after production"):
        Orchestrator().reject(workflow, reason="Not ready", actor_id="reviewer-1")

def test_completed_workflow_cannot_advance() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.COMPLETED
    workflow.status = WorkflowStatus.COMPLETED

    with pytest.raises(InvalidTransitionError, match="Cannot advance"):
        Orchestrator().advance(workflow)


def test_production_accepts_legacy_safety_artifact_without_finding_category_fields() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.PRODUCTION
    workflow.status = WorkflowStatus.ACTIVE
    workflow.artifacts["content"] = ContentDraft(
        title="Educational topic",
        audience="general public",
        body="A supported educational claim [nih-1].",
        cited_source_ids=["nih-1"],
        disclaimer="Educational information only; not medical advice.",
    ).model_dump(mode="json")
    workflow.artifacts["safety"] = {
        "approved": True,
        "ruleset_version": "task-6a-v0",
        "findings": [
            {
                "severity": "warning",
                "code": "editorial_clarity",
                "message": "Legacy finding without category metadata.",
            }
        ],
    }

    legacy_review = SafetyReview.model_validate(workflow.artifacts["safety"])
    assert legacy_review.findings[0].category == "editorial"
    assert legacy_review.findings[0].ruleset_version == "legacy"

    Orchestrator().advance(workflow)

    assert workflow.stage == WorkflowStage.HUMAN_REVIEW
    assert workflow.status == WorkflowStatus.AWAITING_HUMAN


def test_legacy_safety_finding_with_unknown_code_requires_category() -> None:
    with pytest.raises(ValueError, match="must include category"):
        SafetyReview.model_validate(
            {
                "approved": False,
                "ruleset_version": "task-6a-v0",
                "findings": [
                    {
                        "severity": "blocking",
                        "code": "legacy_unknown_code",
                        "message": "Legacy finding without category metadata.",
                    }
                ],
            }
        )
