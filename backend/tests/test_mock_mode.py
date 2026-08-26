import json
from types import SimpleNamespace

import pytest

from app.services.billing_service import PaystackService
from app.services.llm_orchestration_service import LLMOrchestrationService
from app.services.smtp_service import SMTPService


@pytest.mark.asyncio
async def test_mock_llm_is_offline_and_deterministic():
    service = LLMOrchestrationService()
    first = await service.call_llm("Classify this email", feature="classification")
    second = await service.call_llm("Classify this email", feature="classification")

    assert first == second
    assert first["provider"] == "mock"
    assert json.loads(first["response"])["category"] == "Work"


@pytest.mark.asyncio
async def test_mock_payment_succeeds_without_credentials():
    result = await PaystackService().initialize_payment(
        email="developer@example.test",
        amount=1000,
        reference="test-reference",
        currency="USD",
    )

    assert result["success"] is True
    assert result["mock"] is True
    assert result["authorization_url"].startswith("http://localhost:3000/")


@pytest.mark.asyncio
async def test_mock_email_does_not_read_credentials_or_open_smtp():
    account = SimpleNamespace(email="sender@example.test")
    success, message = await SMTPService().send_email(
        account=account,
        db=None,
        to="recipient@example.test",
        subject="Offline test",
        body_text="Hello",
    )

    assert success is True
    assert "mock" in message.lower()
