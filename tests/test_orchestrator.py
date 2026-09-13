import pytest
from pydantic import ValidationError

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


def test_legacy_safety_artifact_without_metadata_can_advance_from_production() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.PRODUCTION
    workflow.artifacts["content"] = {
        "title": "Educational topic",
        "audience": "general public",
        "body": "Supported educational copy.",
        "cited_source_ids": ["nih-1"],
        "disclaimer": "Educational information only; not medical advice.",
    }
    workflow.artifacts["safety"] = {
        "approved": True,
        "findings": [
            {
                "severity": "warning",
                "code": "absolute_medical_claim",
                "message": "Replace absolute medical language with evidence-calibrated wording.",
                "matched_text": "always",
            }
        ],
    }

    assert "ruleset_version" not in workflow.artifacts["safety"]
    assert "category" not in workflow.artifacts["safety"]["findings"][0]
    assert "ruleset_version" not in workflow.artifacts["safety"]["findings"][0]

    Orchestrator().advance(workflow)

    assert workflow.stage == WorkflowStage.HUMAN_REVIEW
    assert workflow.status == WorkflowStatus.AWAITING_HUMAN
    assert workflow.artifacts["production"]["publish_ready"] is False


def test_malformed_current_safety_artifact_still_fails_validation() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.PRODUCTION
    workflow.artifacts["content"] = {
        "title": "Educational topic",
        "audience": "general public",
        "body": "Supported educational copy.",
        "cited_source_ids": ["nih-1"],
        "disclaimer": "Educational information only; not medical advice.",
    }
    workflow.artifacts["safety"] = {
        "approved": True,
        "ruleset_version": "task-6a-v1",
        "findings": [
            {
                "category": "editorial",
                "severity": "warning",
                "code": "absolute_medical_claim",
                "message": "Replace absolute medical language with evidence-calibrated wording.",
                "matched_text": "always",
            }
        ],
    }

    with pytest.raises(ValidationError, match="ruleset_version"):
        Orchestrator().advance(workflow)


def test_mixed_legacy_and_unknown_metadata_missing_findings_fail_validation() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.PRODUCTION
    workflow.artifacts["content"] = {
        "title": "Educational topic",
        "audience": "general public",
        "body": "Supported educational copy.",
        "cited_source_ids": ["nih-1"],
        "disclaimer": "Educational information only; not medical advice.",
    }
    workflow.artifacts["safety"] = {
        "approved": True,
        "findings": [
            {
                "severity": "warning",
                "code": "absolute_medical_claim",
                "message": "Replace absolute medical language with evidence-calibrated wording.",
                "matched_text": "always",
            },
            {
                "severity": "warning",
                "code": "unexpected_code",
                "message": "Unexpected malformed finding.",
            },
        ],
    }

    with pytest.raises(ValidationError, match="category"):
        Orchestrator().advance(workflow)


def test_completed_workflow_cannot_advance() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.COMPLETED
    workflow.status = WorkflowStatus.COMPLETED

    with pytest.raises(InvalidTransitionError, match="Cannot advance"):
        Orchestrator().advance(workflow)
