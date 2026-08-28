import pytest

from app.services.email import EmailService, EmailValidationError, validate_email_payload
from app.services.email.providers import GmailProviderAdapter, OutlookProviderAdapter
from app.services.email_service import EmailService as LegacyEmailService
from app.services.llm import LLMOrchestrationService, ModelRegistry
from app.services.llm_orchestration_service import LLMOrchestrationService as LegacyLLMService


def test_legacy_service_imports_point_to_decomposed_implementations():
    assert LegacyEmailService is EmailService
    assert LegacyLLMService is LLMOrchestrationService
    assert ModelRegistry.get_model("gemini-1.5-flash")["provider"] == "google"


def test_email_payload_validation_normalizes_addresses():
    payload = validate_email_payload({"sender": " Person@Example.COM ", "subject": "Hello"})
    assert payload["sender"] == "person@example.com"


def test_email_payload_validation_rejects_invalid_sender():
    with pytest.raises(EmailValidationError, match="Invalid sender"):
        validate_email_payload({"sender": "bad@email", "subject": "Hello"})


@pytest.mark.asyncio
async def test_provider_adapters_delegate_to_established_transports(mocker):
    transport = mocker.Mock()
    transport._send_gmail_reply = mocker.AsyncMock(return_value=True)
    transport._send_outlook_reply = mocker.AsyncMock(return_value=True)
    payload = {"original_email_id": "message-1", "recipient": "person@example.com"}

    assert await GmailProviderAdapter().send(transport, payload) is True
    assert await OutlookProviderAdapter().send(transport, payload) is True
    transport._send_gmail_reply.assert_awaited_once_with("message-1", payload)
    transport._send_outlook_reply.assert_awaited_once_with("message-1", payload)
