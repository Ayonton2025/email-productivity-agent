import json

from app.services.mock_services import mock_llm_response, mock_payment


def test_mock_llm_response_is_deterministic_and_marked_mock():
    first = mock_llm_response("  Please summarize this email. ", "summary", "local")
    second = mock_llm_response(" Please summarize this email. ", "summary", "local")
    assert first == second
    assert first["mock"] is True
    assert json.loads(first["response"])["summary"] == "Please summarize this email."


def test_mock_payment_uses_stable_reference():
    payment = mock_payment("ref-123", 400, "USD", "user@example.test")
    assert payment["payment_status"] == "completed"
    assert payment["access_code"].startswith("mock_")
    assert payment["authorization_url"].endswith("reference=ref-123")
