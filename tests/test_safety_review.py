from pathlib import Path

from fastapi.testclient import TestClient

from content_os.main import app
from content_os.models.content import ContentDraft
from content_os.models.evidence import ApprovedClaim, EvidenceOutput
from content_os.models.workflow import Workflow, WorkflowStage, WorkflowStatus
from content_os.orchestration.orchestrator import Orchestrator
from content_os.persistence.database import build_engine, initialize_database
from content_os.persistence.repository import SqlWorkflowRepository
from content_os.safety import SAFETY_RULESET_VERSION, MedicalEditorialReviewEngine

client = TestClient(app)


def evidence(*source_ids: str) -> EvidenceOutput:
    return EvidenceOutput(
        claims=[
            ApprovedClaim(
                text="Supported educational claim.",
                source_ids=list(source_ids),
                structurally_supported=True,
            )
        ],
        limitations=["Structural linkage only."],
    )


def draft(
    body: str = "A supported educational claim [nih-1].",
    source_ids: list[str] | None = None,
    disclaimer: str = "Educational information only; not medical advice.",
) -> ContentDraft:
    return ContentDraft(
        title="Educational topic",
        audience="general public",
        body=body,
        cited_source_ids=["nih-1"] if source_ids is None else source_ids,
        disclaimer=disclaimer,
    )


def finding_codes(review: object) -> list[str]:
    return [finding.code for finding in review.findings]


def test_supported_educational_draft_passes_without_findings() -> None:
    review = MedicalEditorialReviewEngine().review(draft(), evidence("nih-1"))

    assert review.approved is True
    assert review.findings == []
    assert review.ruleset_version == SAFETY_RULESET_VERSION


def test_evidence_and_disclaimer_failures_are_blocking_and_ordered() -> None:
    review = MedicalEditorialReviewEngine().review(
        draft(body="", source_ids=["unknown"], disclaimer="For education."),
        evidence("nih-1"),
    )

    assert review.approved is False
    assert finding_codes(review) == [
        "no_supported_claims",
        "unsupported_source_reference",
        "missing_disclaimer",
    ]
    assert all(finding.ruleset_version == SAFETY_RULESET_VERSION for finding in review.findings)
    assert review.findings[1].matched_text == "unknown"


def test_missing_citations_is_blocking() -> None:
    review = MedicalEditorialReviewEngine().review(
        draft(source_ids=[]),
        evidence("nih-1"),
    )

    assert review.approved is False
    assert finding_codes(review) == ["missing_citations"]


def test_personalized_diagnosis_and_treatment_instructions_are_blocking() -> None:
    review = MedicalEditorialReviewEngine().review(
        draft(body="You have diabetes. You should stop taking this medicine."),
        evidence("nih-1"),
    )

    assert review.approved is False
    assert "personalized_medical_instruction" in finding_codes(review)


def test_medication_dose_instruction_is_blocking() -> None:
    review = MedicalEditorialReviewEngine().review(
        draft(body="Start metformin 500 mg tonight."),
        evidence("nih-1"),
    )

    assert review.approved is False
    assert finding_codes(review) == ["medication_dose_instruction"]
    assert review.findings[0].matched_text == "Start metformin 500 mg"


def test_medication_initiation_or_dose_change_without_numeric_amount_is_blocking() -> None:
    review = MedicalEditorialReviewEngine().review(
        draft(body="Start metformin tonight. Increase your insulin dose."),
        evidence("nih-1"),
    )

    assert review.approved is False
    assert "medication_dose_instruction" in finding_codes(review)


def test_non_instructional_medication_sentence_is_not_flagged() -> None:
    review = MedicalEditorialReviewEngine().review(
        draft(body="We should increase awareness of medication safety in communities."),
        evidence("nih-1"),
    )

    assert review.approved is True
    assert "medication_dose_instruction" not in finding_codes(review)


def test_generic_medication_initiation_wording_without_specific_treatment_is_not_flagged() -> None:
    review = MedicalEditorialReviewEngine().review(
        draft(body="Start medication only after speaking with your clinician."),
        evidence("nih-1"),
    )

    assert review.approved is True
    assert "medication_dose_instruction" not in finding_codes(review)


def test_absolute_cure_and_clarity_language_produce_warnings_only() -> None:
    long_sentence = " ".join(["word"] * 41) + "."
    review = MedicalEditorialReviewEngine().review(
        draft(body=f"This always cures insulin resistance and guarantees success. {long_sentence}"),
        evidence("nih-1"),
    )

    assert review.approved is True
    assert finding_codes(review) == [
        "absolute_medical_claim",
        "cure_or_guarantee_language",
        "editorial_clarity",
    ]
    assert all(finding.severity == "warning" for finding in review.findings)


def warning_workflow() -> Workflow:
    from content_os.models.evidence import ClaimCandidate, SourceCandidate

    return Workflow(
        topic="Balanced metabolic health education",
        audience="general public",
        sources=[
            SourceCandidate(
                id="nih-1",
                title="Authoritative source",
                publisher="NIDDK",
                url="https://www.niddk.nih.gov/health-information",
            )
        ],
        claims=[
            ClaimCandidate(
                text="This approach always improves metabolic health.",
                source_ids=["nih-1"],
            )
        ],
    )


def test_warning_only_workflow_reaches_human_gate_but_is_not_publish_ready() -> None:
    workflow = warning_workflow()
    orchestrator = Orchestrator()

    for _ in range(5):
        orchestrator.advance(workflow)

    assert workflow.stage == WorkflowStage.HUMAN_REVIEW
    assert workflow.status == WorkflowStatus.AWAITING_HUMAN
    assert workflow.artifacts["safety"]["approved"] is True
    assert workflow.artifacts["safety"]["ruleset_version"] == SAFETY_RULESET_VERSION
    assert workflow.artifacts["safety"]["findings"][0]["severity"] == "warning"
    assert workflow.artifacts["production"]["publish_ready"] is False


def test_blocking_instruction_preserves_revision_loop() -> None:
    workflow = warning_workflow()
    workflow.claims[0].text = "Increase metformin to 1000 mg daily."
    orchestrator = Orchestrator()

    for _ in range(4):
        orchestrator.advance(workflow)

    assert workflow.stage == WorkflowStage.CONTENT
    assert workflow.status == WorkflowStatus.REVISION_REQUIRED
    assert workflow.revision_count == 1
    assert workflow.history[-1].note == "Safety revision required"


def test_structured_safety_artifact_survives_persistence(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'task6a.db'}")
    initialize_database(engine)
    repository = SqlWorkflowRepository(engine)
    workflow = warning_workflow()
    repository.create(workflow)
    orchestrator = Orchestrator()

    for _ in range(4):
        orchestrator.advance(workflow)
    repository.save(workflow)

    loaded = SqlWorkflowRepository(engine).get(workflow.id)

    assert loaded is not None
    assert loaded.artifacts["safety"] == workflow.artifacts["safety"]
    assert loaded.artifacts["safety"]["ruleset_version"] == SAFETY_RULESET_VERSION
    assert loaded.history[-1].action == "advance"


def test_warning_only_api_workflow_still_requires_human_approval() -> None:
    created = client.post(
        "/api/v1/workflows",
        json={
            "topic": "Balanced metabolic health education",
            "sources": [
                {
                    "id": "nih-1",
                    "title": "Authoritative source",
                    "publisher": "NIDDK",
                    "url": "https://www.niddk.nih.gov/health-information",
                }
            ],
            "claims": [
                {
                    "text": "This approach always improves metabolic health.",
                    "source_ids": ["nih-1"],
                }
            ],
        },
    )
    assert created.status_code == 201
    workflow_id = created.json()["id"]

    for _ in range(5):
        response = client.post(f"/api/v1/workflows/{workflow_id}/advance")
        assert response.status_code == 200

    payload = response.json()
    assert payload["stage"] == "human_review"
    assert payload["status"] == "awaiting_human"
    assert payload["artifacts"]["production"]["publish_ready"] is False
    assert payload["artifacts"]["safety"]["findings"][0]["severity"] == "warning"
