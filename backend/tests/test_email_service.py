from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import smtp_service as smtp_module
from app.services.smtp_service import SMTPService


def account():
    return SimpleNamespace(
        email="sender@example.test",
        encrypted_password="encrypted",
        smtp_host="smtp.example.test",
        smtp_port=587,
        use_tls=True,
        imap_host="imap.example.test",
        imap_port=993,
        provider="imap",
        email_account_type="external",
    )


@pytest.mark.asyncio
async def test_mock_send_succeeds_without_account_credentials():
    success, message = await SMTPService().send_email(
        account=SimpleNamespace(email="sender@example.test"),
        db=None,
        to="recipient@example.test",
        subject="Hello",
        body_text="Body",
    )
    assert success is True
    assert "mock" in message.lower()


@pytest.mark.asyncio
async def test_plain_text_message_headers(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    monkeypatch.setattr(smtp_module, "decrypt_credential", lambda value: "password")
    captured = {}

    class FakeSMTP:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def login(self, *args):
            return None

        async def send_message(self, message):
            captured["message"] = message

    service = SMTPService()
    monkeypatch.setattr(smtp_module.aiosmtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(service, "_append_to_sent", lambda *args: _true())
    success, _ = await service.send_email(account(), None, "to@example.test", "Subject", "Hello")
    assert success is True
    assert captured["message"]["To"] == "to@example.test"
    assert captured["message"]["Subject"] == "Subject"


async def _true():
    return True


@pytest.mark.asyncio
async def test_html_template_creates_alternative_message(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    monkeypatch.setattr(smtp_module, "decrypt_credential", lambda value: "password")
    captured = {}

    class FakeSMTP:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def login(self, *args):
            return None

        async def send_message(self, message):
            captured["message"] = message

    service = SMTPService()
    monkeypatch.setattr(smtp_module.aiosmtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(service, "_append_to_sent", lambda *args: _true())
    success, _ = await service.send_email(
        account(), None, "to@example.test", "Subject", "Plain", "<strong>HTML</strong>"
    )
    assert success is True
    assert captured["message"].get_content_type() == "multipart/alternative"
    assert len(captured["message"].get_payload()) == 2


@pytest.mark.asyncio
async def test_smtp_failure_returns_false_after_retries(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    monkeypatch.setattr(settings, "SMTP_MAX_RETRIES", 2)
    monkeypatch.setattr(smtp_module, "decrypt_credential", lambda value: "password")
    monkeypatch.setattr(smtp_module.asyncio, "sleep", _no_sleep)
    attempts = {"count": 0}

    class FailingSMTP:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            attempts["count"] += 1
            raise ConnectionError("SMTP unavailable")

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(smtp_module.aiosmtplib, "SMTP", FailingSMTP)
    success, message = await SMTPService().send_email(account(), None, "to@example.test", "Subject", "Body")
    assert success is False
    assert attempts["count"] == 2
    assert "unavailable" in message


async def _no_sleep(*args):
    return None


@pytest.mark.asyncio
async def test_transient_smtp_failure_is_retried(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    monkeypatch.setattr(settings, "SMTP_MAX_RETRIES", 3)
    monkeypatch.setattr(smtp_module, "decrypt_credential", lambda value: "password")
    monkeypatch.setattr(smtp_module.asyncio, "sleep", _no_sleep)
    attempts = {"count": 0}

    class FlakySMTP:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ConnectionError("temporary")
            return self

        async def __aexit__(self, *args):
            return None

        async def login(self, *args):
            return None

        async def send_message(self, message):
            return None

    service = SMTPService()
    monkeypatch.setattr(smtp_module.aiosmtplib, "SMTP", FlakySMTP)
    monkeypatch.setattr(service, "_append_to_sent", lambda *args: _true())
    success, _ = await service.send_email(account(), None, "to@example.test", "Subject", "Body")
    assert success is True
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_hosted_abuse_rejection_prevents_delivery(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)
    hosted = account()
    hosted.email_account_type = "hosted_internal"
    service = SMTPService()

    async def deny(**kwargs):
        return {"allowed": False, "reason": "daily limit", "spam_score": 0, "link_count": 0}

    async def record(**kwargs):
        return None

    monkeypatch.setattr(service.hosted_abuse_service, "evaluate_send_permission", deny)
    monkeypatch.setattr(service.hosted_abuse_service, "record_send_attempt", record)
    success, message = await service.send_email(hosted, None, "to@example.test", "Subject", "Body")
    assert success is False
    assert "daily limit" in message
