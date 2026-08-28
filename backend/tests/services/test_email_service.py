from types import SimpleNamespace

import pytest

from app.services.email_provider_service import EmailProviderService
from app.services.email_service import EmailService


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@pytest.mark.asyncio
async def test_duplicate_email_is_returned_without_creating_a_second_record(mocker):
    existing = SimpleNamespace(to_dict=mocker.Mock(return_value={"id": "existing", "subject": "Quarterly review"}))
    db = SimpleNamespace(execute=mocker.AsyncMock(return_value=ScalarResult(existing)))
    service = EmailService(db)

    duplicate = await service._check_duplicate_email(
        "user-1",
        {"sender": "manager@example.com", "subject": "Quarterly review", "body": "Same message"},
    )

    assert duplicate == {"id": "existing", "subject": "Quarterly review"}
    db.execute.assert_awaited_once()
    assert not hasattr(db, "add")


@pytest.mark.asyncio
async def test_gmail_failure_calls_configured_outlook_fallback(mocker):
    service = EmailProviderService()
    service.gmail_service = object()
    service.outlook_access_token = "outlook-token"
    gmail = mocker.patch.object(service, "_send_gmail_reply", new=mocker.AsyncMock(return_value=False))
    outlook = mocker.patch.object(service, "_send_outlook_reply", new=mocker.AsyncMock(return_value=True))
    draft = {"recipient": "Customer@Example.com", "subject": "Re: Hello", "body": "Thanks"}

    sent = await service.send_email_reply("gmail", "message-1", draft)

    assert sent is True
    gmail.assert_awaited_once()
    outlook.assert_awaited_once_with(
        "message-1",
        {"recipient": "customer@example.com", "subject": "Re: Hello", "body": "Thanks"},
    )


@pytest.mark.asyncio
async def test_invalid_recipient_is_rejected_before_any_provider_call(mocker):
    service = EmailProviderService()
    service.gmail_service = object()
    gmail = mocker.patch.object(service, "_send_gmail_reply", new=mocker.AsyncMock())

    with pytest.raises(ValueError, match="Invalid recipient email address"):
        await service.send_email_reply(
            "gmail",
            "message-1",
            {"recipient": "bad@email", "subject": "Hello", "body": "Body"},
        )

    gmail.assert_not_awaited()
