import pytest
from pydantic import BaseModel

from content_os.agents.production import ProductionAgent
from content_os.models.content import ContentDraft
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


def test_production_agent_accepts_legacy_safety_artifacts() -> None:
    class LegacyFinding(BaseModel):
        severity: str
        code: str
        message: str

    class LegacySafetyArtifact(BaseModel):
        approved: bool
        findings: list[LegacyFinding]

    workflow = valid_workflow()
    workflow.stage = WorkflowStage.PRODUCTION
    workflow.artifacts["content"] = ContentDraft(
        title="Educational topic",
        audience="general public",
        body="Supported educational claim [nih-1].",
        cited_source_ids=["nih-1"],
        disclaimer="Educational information only; not medical advice.",
    ).model_dump(mode="json")
    workflow.artifacts["safety"] = LegacySafetyArtifact(
        approved=True,
        findings=[
            LegacyFinding(
                severity="warning",
                code="legacy_warning",
                message="Legacy finding payload.",
            )
        ],
    )

    package = ProductionAgent().run(workflow)

    assert package.title == "Educational topic"
    assert package.source_ids == ["nih-1"]
    assert "category" not in workflow.artifacts["safety"].findings[0].model_dump()


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


def test_production_accepts_review_ruleset_backfill_for_findings() -> None:
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
        "ruleset_version": "2026.09",
        "findings": [
            {
                "category": "medical_safety",
                "severity": "warning",
                "code": "medication_instruction",
                "message": "Avoid medication-specific treatment instructions.",
            }
        ],
    }

    Orchestrator().advance(workflow)

    assert workflow.stage == WorkflowStage.HUMAN_REVIEW
    assert workflow.status == WorkflowStatus.AWAITING_HUMAN
    assert workflow.artifacts["production"]["publish_ready"] is False


def test_completed_workflow_cannot_advance() -> None:
    workflow = valid_workflow()
    workflow.stage = WorkflowStage.COMPLETED
    workflow.status = WorkflowStatus.COMPLETED

    with pytest.raises(InvalidTransitionError, match="Cannot advance"):
        Orchestrator().advance(workflow)
