import base64
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.email import gmail_client, gmail_html
from app.services.email.gmail_client import GmailClient
from app.services.email.gmail_message_parser import GmailMessageParser
from app.services.email.gmail_processing import GmailAIProcessor


def body(mime, text):
    return {"mimeType": mime, "body": {"data": base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")}}


def test_nested_multipart_metadata_flags_and_utc():
    parsed = GmailMessageParser().parse_gmail_message(
        {
            "id": "opaque-id",
            "threadId": "thread",
            "internalDate": "1705320000000",
            "labelIds": ["UNREAD", "STARRED", "SPAM", "DRAFT"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "a@example.com, b@example.com"},
                    {"name": "Cc", "value": "c@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 15:00:00 +0300"},
                ],
                "parts": [
                    {
                        "mimeType": "multipart/alternative",
                        "parts": [body("text/plain", "Plain"), body("text/html", "<b>HTML</b>")],
                    },
                    {
                        "filename": "report.pdf",
                        "mimeType": "application/pdf",
                        "body": {"size": 123, "attachmentId": "att-1"},
                    },
                ],
            },
        }
    )
    assert parsed["body_text"] == "Plain" and parsed["body_html"] == "<b>HTML</b>"
    assert parsed["received_at"] == datetime(2024, 1, 15, 12)
    assert parsed["uid"] == 1705320000000
    assert parsed["recipients"] == ["a@example.com", "b@example.com"]
    assert parsed["cc"] == ["c@example.com"]
    assert not parsed["is_read"] and parsed["is_flagged"] and parsed["is_spam"] and parsed["is_draft"]
    assert parsed["attachments"] == [
        {"filename": "report.pdf", "mime_type": "application/pdf", "size": 123, "attachment_id": "att-1"}
    ]


@pytest.mark.parametrize("internal_date", [None, "invalid", "-1", str(2**64)])
def test_uid_falls_back_to_utc_received_timestamp(internal_date):
    parsed = GmailMessageParser().parse_gmail_message(
        {
            "id": "not-a-number",
            "internalDate": internal_date,
            "payload": {"headers": [{"name": "Date", "value": "Mon, 15 Jan 2024 12:00:00 +0000"}]},
        }
    )
    assert parsed["uid"] == 1705320000000
    assert parsed["sender"] == "Unknown" and parsed["subject"] == "(No Subject)"
    assert parsed["body_text"] == parsed["body_html"] == ""


def test_parser_invalid_payload_raises():
    with pytest.raises(KeyError):
        GmailMessageParser().parse_gmail_message({"id": "missing-payload"})


def test_html_fallback_removes_scripts_and_event_handlers(monkeypatch):
    monkeypatch.setattr(gmail_html, "HAS_BLEACH", False)
    result = gmail_html.GmailHtmlProcessor()._sanitize_html('<p onclick="bad()">Safe</p><script>bad()</script>')
    assert "bad()" not in result and "Safe" in result


def test_optional_bleach_configuration_and_link_protection(monkeypatch):
    clean = Mock(return_value='<a href="https://example.com">Link</a>')
    monkeypatch.setattr(gmail_html, "HAS_BLEACH", True)
    monkeypatch.setattr(gmail_html, "bleach_clean", clean, raising=False)
    result = gmail_html.GmailHtmlProcessor()._sanitize_html("input")
    assert 'rel="noopener noreferrer"' in result
    assert clean.call_args.kwargs["strip"] is True
    assert "script" not in clean.call_args.kwargs["tags"]


def test_cid_without_downloadable_metadata_stays_unchanged():
    html = '<img src="cid:unresolved">'
    assert gmail_html.GmailHtmlProcessor()._resolve_cid_images(html, []) == html


def test_build_client_uses_supplied_oauth_token(monkeypatch):
    credentials = Mock()
    build = Mock(return_value="gmail-service")
    monkeypatch.setattr(gmail_client, "Credentials", credentials)
    monkeypatch.setattr(gmail_client, "build", build)
    assert GmailClient(None).build_gmail_service("test-token") == "gmail-service"
    credentials.assert_called_once_with(token="test-token")
    build.assert_called_once_with("gmail", "v1", credentials=credentials.return_value)


@pytest.mark.asyncio
async def test_fetch_skips_individual_failure_and_preserves_order():
    service = Mock()
    api = service.users.return_value.messages.return_value
    api.list.return_value.execute.return_value = {"messages": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
    api.get.return_value.execute.side_effect = [{"id": "a"}, RuntimeError("provider error"), {"id": "c"}]
    result = await GmailClient(None).fetch_last_n_emails(service, n=90, query="in:inbox")
    assert result == [{"id": "a"}, {"id": "c"}]
    api.list.assert_called_once_with(userId="me", maxResults=50, q="in:inbox")


@pytest.mark.asyncio
async def test_fetch_empty_and_list_failure():
    service = Mock()
    api = service.users.return_value.messages.return_value
    api.list.return_value.execute.return_value = {}
    assert await GmailClient(None).fetch_last_n_emails(service) == []
    api.get.assert_not_called()
    api.list.return_value.execute.side_effect = RuntimeError("list failure")
    with pytest.raises(RuntimeError):
        await GmailClient(None).fetch_last_n_emails(service)


@pytest.mark.asyncio
async def test_watch_updates_history_and_expiration_only_on_success():
    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    account = SimpleNamespace(id="account-1", email="user@example.com", history_id=None, watch_expiration=None)
    service = Mock()
    service.users.return_value.watch.return_value.execute.return_value = {
        "historyId": "99",
        "expiration": "1705320000000",
    }
    assert await GmailClient(db).setup_gmail_push(service, account, "projects/test/topics/gmail") is True
    assert account.history_id == "99" and account.watch_expiration == datetime(2024, 1, 15, 12)
    db.commit.assert_awaited_once()
    service.users.return_value.watch.return_value.execute.side_effect = RuntimeError("watch error")
    assert await GmailClient(db).setup_gmail_push(service, account, "topic") is False
    assert account.history_id == "99"


@pytest.mark.asyncio
async def test_ai_processing_and_provider_fallback():
    email = SimpleNamespace(
        id="email",
        sender="sender@example.com",
        subject="Subject",
        body_text="Body",
        body_html="",
        processing_status="pending",
    )
    result = Mock()
    result.scalar_one_or_none.return_value = email
    db = SimpleNamespace(execute=AsyncMock(return_value=result), commit=AsyncMock(), rollback=AsyncMock())
    prompts = SimpleNamespace(get_active_prompt=AsyncMock(return_value=SimpleNamespace(template="Prompt")))
    llm = SimpleNamespace(process_prompt=AsyncMock(side_effect=[RuntimeError("AI failure"), " Summary "]))
    assert await GmailAIProcessor(db, llm, prompts).process_emails_with_ai(["email"]) == 1
    assert email.ai_category == "Uncategorized" and email.ai_summary == "Summary"
    assert email.processing_status == "completed"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ai_skips_missing_prompts_and_completed_messages():
    db = SimpleNamespace(execute=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    prompts = SimpleNamespace(get_active_prompt=AsyncMock(return_value=None))
    llm = SimpleNamespace(process_prompt=AsyncMock())
    processor = GmailAIProcessor(db, llm, prompts)
    assert await processor.process_emails_with_ai(["email"]) == 0
    db.execute.assert_not_awaited()
    prompts.get_active_prompt.return_value = SimpleNamespace(template="Prompt")
    result = Mock()
    result.scalar_one_or_none.side_effect = [None, SimpleNamespace(processing_status="completed")]
    db.execute.return_value = result
    assert await processor.process_emails_with_ai(["missing", "done"]) == 0
    llm.process_prompt.assert_not_awaited()
    db.commit.assert_not_awaited()
