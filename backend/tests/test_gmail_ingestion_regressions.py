"""Regression cases for Gmail ingestion, using synthetic messages only."""

import base64
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.gmail_ingestion_service import GmailIngestionService


def message(mime="text/plain", content="Plain body"):
    return {
        "id": "18ab93cd45ef",
        "internalDate": "1705320000000",
        "threadId": "thread-1",
        "payload": {
            "mimeType": mime,
            "headers": [{"name": "Date", "value": "Mon, 15 Jan 2024 12:00:00 +0000"}],
            "body": {"data": base64.urlsafe_b64encode(content.encode()).decode().rstrip("=")},
        },
    }


def test_plain_text_does_not_become_html():
    service = GmailIngestionService.__new__(GmailIngestionService)
    parsed = service.parse_gmail_message(message())
    assert parsed["body_text"] == "Plain body"
    assert parsed["body_html"] == ""


def test_html_body_and_text_fallback_are_not_swapped():
    service = GmailIngestionService.__new__(GmailIngestionService)
    parsed = service.parse_gmail_message(message("text/html", "<p>HTML body</p>"))
    assert parsed["body_html"] == "<p>HTML body</p>"
    assert parsed["body_text"] == "HTML body"


@pytest.mark.asyncio
async def test_hexadecimal_gmail_id_can_be_stored():
    service = GmailIngestionService.__new__(GmailIngestionService)
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session = SimpleNamespace(
        execute=AsyncMock(return_value=result), add=Mock(), flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock()
    )
    service.db = session
    parsed = message()
    data = {
        "external_id": parsed["id"],
        "message_id": parsed["id"],
        "uid": 1705320000000,
        "sender": "sender@example.com",
        "subject": "Test",
        "received_at": datetime(2024, 1, 15, 12),
    }
    await service.store_emails("user-1", "account-1", [data])
    assert session.add.call_args.args[0].uid == 1705320000000
    session.commit.assert_awaited_once()
