import pytest

from content_os.agents.production import ProductionAgent
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


def test_production_accepts_legacy_safety_findings() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.PRODUCTION
    workflow.status = WorkflowStatus.ACTIVE
    workflow.artifacts["content"] = {
        "title": "Insulin resistance overview",
        "audience": "general public",
        "body": "Insulin resistance can precede type 2 diabetes.",
        "cited_source_ids": ["nih-1"],
        "disclaimer": "Educational content only.",
    }
    workflow.artifacts["safety"] = {
        "approved": True,
        "findings": [
            {
                "severity": "warning",
                "code": "medication_instruction",
                "message": "Avoid medication-specific treatment instructions.",
                "matched_text": "Start metformin 500 mg tonight.",
            }
        ],
    }

    Orchestrator().advance(workflow)

    assert workflow.stage == WorkflowStage.HUMAN_REVIEW
    assert workflow.status == WorkflowStatus.AWAITING_HUMAN
    assert workflow.artifacts["production"]["publish_ready"] is False


def test_production_backfills_finding_ruleset_from_review() -> None:
    artifact = {
        "approved": True,
        "ruleset_version": "2026.09",
        "findings": [
            {
                "severity": "warning",
                "code": "medication_instruction",
                "message": "Avoid medication-specific treatment instructions.",
                "matched_text": "Start metformin 500 mg tonight.",
            }
        ],
    }

    normalized = ProductionAgent()._with_legacy_safety_defaults(artifact)

    assert normalized["findings"][0]["ruleset_version"] == "2026.09"


def test_production_preserves_blank_review_ruleset_without_finding_backfill() -> None:
    artifact = {
        "approved": True,
        "ruleset_version": "",
        "findings": [
            {
                "category": "medical_safety",
                "severity": "warning",
                "code": "medication_instruction",
                "message": "Avoid medication-specific treatment instructions.",
                "ruleset_version": "2026.09",
            }
        ],
    }

    normalized = ProductionAgent()._with_legacy_safety_defaults(artifact)

    assert normalized is artifact


def test_production_backfills_blank_review_ruleset_when_finding_is_missing_it() -> None:
    artifact = {
        "approved": True,
        "ruleset_version": "",
        "findings": [
            {
                "category": "medical_safety",
                "severity": "warning",
                "code": "medication_instruction",
                "message": "Avoid medication-specific treatment instructions.",
            }
        ],
    }

    normalized = ProductionAgent()._with_legacy_safety_defaults(artifact)

    assert normalized["ruleset_version"] == "1.0.0"
    assert normalized["findings"][0]["ruleset_version"] == "1.0.0"


def test_completed_workflow_cannot_advance() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.COMPLETED
    workflow.status = WorkflowStatus.COMPLETED

    with pytest.raises(InvalidTransitionError, match="Cannot advance"):
        Orchestrator().advance(workflow)
