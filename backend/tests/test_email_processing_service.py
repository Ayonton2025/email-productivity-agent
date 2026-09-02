from unittest.mock import AsyncMock

import pytest

from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_load_mock_emails_does_not_duplicate_populated_inbox(db_session, monkeypatch):
    service = EmailService(db_session)
    existing = [{"id": str(index)} for index in range(5)]
    monkeypatch.setattr(service, "get_user_emails", AsyncMock(return_value=existing))
    process = AsyncMock()
    monkeypatch.setattr(service, "process_single_email", process)

    assert await service.load_mock_emails("user-1") == existing
    process.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_single_email_persists_and_returns_email(db_session):
    service = EmailService(db_session)
    result = await service.process_single_email(
        {
            "sender": "sender@example.test",
            "subject": "Status update",
            "body": "The deployment completed.",
            "timestamp": "2026-01-02T03:04:05Z",
            "category": "Updates",
        },
        "user-1",
    )

    assert result["user_id"] == "user-1"
    assert result["sender"] == "sender@example.test"
    assert result["category"] == "Updates"
    assert result["id"]


@pytest.mark.asyncio
async def test_process_single_email_returns_explicit_error_result(db_session):
    service = EmailService(db_session)
    payload = {"id": "external-1", "subject": "Bad timestamp", "timestamp": "not-a-date"}

    result = await service.process_single_email(payload, "user-1")

    assert result["id"] == "external-1"
    assert "processing_error" in result
    assert "Invalid isoformat" in result["processing_error"]
