from fastapi.testclient import TestClient

from app.main import app


def test_request_logging_returns_correlation_id():
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "request-test-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-test-123"


def test_request_logging_generates_correlation_id():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 36
