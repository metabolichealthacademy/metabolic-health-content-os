from fastapi.testclient import TestClient

from content_os.main import app

client = TestClient(app)


def test_health_check_returns_service_status() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Metabolic Health Content OS",
        "version": "0.1.0",
        "environment": "development",
    }


def test_openapi_includes_health_endpoint() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
