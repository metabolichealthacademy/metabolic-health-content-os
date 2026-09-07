from fastapi.testclient import TestClient

from content_os.main import app

client = TestClient(app)


def test_workflow_api_runs_to_human_gate() -> None:
    created = client.post(
        "/api/v1/workflows",
        json={
            "topic": "Understanding insulin resistance",
            "audience": "general public",
            "sources": [
                {
                    "id": "nih-1",
                    "title": "Insulin Resistance",
                    "publisher": "NIDDK",
                    "url": "https://www.niddk.nih.gov/health-information/diabetes/overview/what-is-diabetes/prediabetes-insulin-resistance",
                }
            ],
            "claims": [
                {"text": "Insulin resistance can precede type 2 diabetes.", "source_ids": ["nih-1"]}
            ],
        },
    )
    assert created.status_code == 201
    workflow_id = created.json()["id"]

    for _ in range(5):
        response = client.post(f"/api/v1/workflows/{workflow_id}/advance")
        assert response.status_code == 200

    assert response.json()["stage"] == "human_review"
    assert response.json()["status"] == "awaiting_human"

    approved = client.post(f"/api/v1/workflows/{workflow_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["stage"] == "completed"


def test_missing_workflow_returns_404() -> None:
    response = client.get("/api/v1/workflows/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_early_approval_returns_conflict() -> None:
    created = client.post("/api/v1/workflows", json={"topic": "A test topic"})
    workflow_id = created.json()["id"]

    response = client.post(f"/api/v1/workflows/{workflow_id}/approve")
    assert response.status_code == 409
