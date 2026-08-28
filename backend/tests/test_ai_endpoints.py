import pytest

from app.api import ai_endpoints


def payload():
    return {
        "sender": "sender@example.test",
        "subject": "Quarterly review",
        "body": "Please review by Friday.",
    }


def test_classify_success_schema(client, monkeypatch):
    async def classify_email(**kwargs):
        return {"category": "TASK", "confidence": 0.94, "reasoning": "Contains a requested action"}

    monkeypatch.setattr(ai_endpoints.llm_service, "classify_email", classify_email)
    response = client.post("/api/v1/ai/classify", json=payload())
    assert response.status_code == 200
    assert response.json() == {
        "category": "TASK",
        "confidence": 0.94,
        "reasoning": "Contains a requested action",
    }


def test_classify_passes_authenticated_tenant(client, monkeypatch):
    captured = {}

    async def classify_email(**kwargs):
        captured.update(kwargs)
        return {"category": "FYI", "confidence": 0.5, "reasoning": "Informational"}

    monkeypatch.setattr(ai_endpoints.llm_service, "classify_email", classify_email)
    assert client.post("/api/v1/ai/classify", json=payload()).status_code == 200
    assert captured["tenant_id"] == "test-user-id"


def test_classify_permission_denied_returns_402(client, monkeypatch):
    async def classify_email(**kwargs):
        raise PermissionError("credits")

    monkeypatch.setattr(ai_endpoints.llm_service, "classify_email", classify_email)
    response = client.post("/api/v1/ai/classify", json=payload())
    assert response.status_code == 402
    assert "credits" in response.json()["detail"].lower()


@pytest.mark.parametrize("missing", ["sender", "subject", "body"])
def test_classify_invalid_request_returns_422(client, missing):
    request = payload()
    request.pop(missing)
    assert client.post("/api/v1/ai/classify", json=request).status_code == 422


def test_classify_llm_unavailable_returns_500(client, monkeypatch):
    async def classify_email(**kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(ai_endpoints.llm_service, "classify_email", classify_email)
    response = client.post("/api/v1/ai/classify", json=payload())
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to classify email"


def test_classify_requires_authentication(unauthenticated_client):
    assert unauthenticated_client.post("/api/v1/ai/classify", json=payload()).status_code in {
        401,
        403,
    }
