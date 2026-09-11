from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.email_models import Email, UserEmailAccount
from app.models.user_models import User
from app.services.email import gmail_persistence
from app.services.email.gmail_persistence import GmailEmailPersistence
from app.services.email.gmail_processing import GmailAIProcessor


def parsed(message_id="18abc"):
    return {
        "message_id": message_id,
        "external_id": message_id,
        "uid": 1705320000000,
        "sender": "sender@example.com",
        "subject": "Private subject",
        "received_at": datetime(2024, 1, 15, 12),
        "body_text": "Private body",
        "attachments": [{"filename": "report.pdf", "attachment_id": "attachment"}],
    }


@pytest.mark.asyncio
async def test_storage_is_idempotent_per_mailbox_not_globally(db_session):
    users = [User(email=f"owner{i}@example.com", password_hash="hash") for i in range(2)]
    db_session.add_all(users)
    await db_session.flush()
    accounts = [
        UserEmailAccount(
            user_id=users[i // 2].id,
            email=f"account{i}@example.com",
            provider="gmail",
            imap_host="imap.example.com",
            smtp_host="smtp.example.com",
            encrypted_password="encrypted",
        )
        for i in range(3)
    ]
    db_session.add_all(accounts)
    await db_session.commit()
    persistence = GmailEmailPersistence(db_session)
    for account in accounts:
        assert len(await persistence.store_emails(account.user_id, account.id, [parsed(), parsed()])) == 1
        assert await persistence.store_emails(account.user_id, account.id, [parsed()]) == []
    emails = (await db_session.execute(select(Email))).scalars().all()
    assert len(emails) == 3
    assert {email.account_id for email in emails} == {account.id for account in accounts}
    assert all(email.uid == 1705320000000 and email.body_text == "Private body" for email in emails)


def session_stub():
    result = Mock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.first.return_value = SimpleNamespace(subscription_status="active", plan="professional")
    session = SimpleNamespace(
        execute=AsyncMock(return_value=result), add=Mock(), commit=AsyncMock(), rollback=AsyncMock()
    )

    async def flush():
        session.add.call_args.args[0].id = "stored-email"

    session.flush = AsyncMock(side_effect=flush)
    return session


@pytest.mark.asyncio
async def test_attachments_use_message_identity_and_queue_after_commit(monkeypatch):
    session = session_stub()
    events = []
    session.commit.side_effect = lambda: events.append("commit")
    download = AsyncMock(return_value=[object()])

    async def queue(**kwargs):
        events.append("queue")
        assert kwargs == {"email_id": "stored-email", "user_id": "owner", "user_plan": "professional"}

    monkeypatch.setattr(gmail_persistence.email_attachment_integration, "process_gmail_attachments", download)
    monkeypatch.setattr(gmail_persistence, "HAS_DOCUMENT_ANALYSIS", True)
    monkeypatch.setattr(
        gmail_persistence,
        "task_handler",
        SimpleNamespace(analyze_email_attachments=AsyncMock(side_effect=queue)),
        raising=False,
    )
    service = object()
    ids = await GmailEmailPersistence(session).store_emails(
        "owner",
        "account",
        [parsed("correct-message")],
        gmail_service=service,
        message_ids=["wrong-after-partial-fetch"],
    )
    assert ids == ["stored-email"]
    assert download.await_args.args[:4] == (service, "correct-message", "stored-email", "owner")
    assert events == ["commit", "queue"]


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_and_does_not_queue(monkeypatch):
    session = session_stub()
    session.commit.side_effect = SQLAlchemyError("private database error")
    queue = AsyncMock()
    monkeypatch.setattr(
        gmail_persistence.email_attachment_integration, "process_gmail_attachments", AsyncMock(return_value=[object()])
    )
    monkeypatch.setattr(gmail_persistence, "HAS_DOCUMENT_ANALYSIS", True)
    monkeypatch.setattr(
        gmail_persistence, "task_handler", SimpleNamespace(analyze_email_attachments=queue), raising=False
    )
    with pytest.raises(SQLAlchemyError):
        await GmailEmailPersistence(session).store_emails("owner", "account", [parsed()], gmail_service=object())
    session.rollback.assert_awaited_once()
    queue.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("download_result", [[], RuntimeError("private attachment error")])
async def test_attachment_failure_does_not_lose_email_or_queue_empty_analysis(monkeypatch, download_result, caplog):
    session = session_stub()
    download = AsyncMock()
    if isinstance(download_result, Exception):
        download.side_effect = download_result
    else:
        download.return_value = download_result
    queue = AsyncMock()
    monkeypatch.setattr(gmail_persistence.email_attachment_integration, "process_gmail_attachments", download)
    monkeypatch.setattr(gmail_persistence, "HAS_DOCUMENT_ANALYSIS", True)
    monkeypatch.setattr(
        gmail_persistence, "task_handler", SimpleNamespace(analyze_email_attachments=queue), raising=False
    )
    assert await GmailEmailPersistence(session).store_emails(
        "owner", "account", [parsed()], gmail_service=object()
    ) == ["stored-email"]
    session.commit.assert_awaited_once()
    queue.assert_not_awaited()
    assert "Private subject" not in caplog.text and "private attachment error" not in caplog.text


@pytest.mark.asyncio
async def test_queue_failure_does_not_rollback_committed_email(monkeypatch):
    session = session_stub()
    monkeypatch.setattr(
        gmail_persistence.email_attachment_integration, "process_gmail_attachments", AsyncMock(return_value=[object()])
    )
    monkeypatch.setattr(gmail_persistence, "HAS_DOCUMENT_ANALYSIS", True)
    monkeypatch.setattr(
        gmail_persistence,
        "task_handler",
        SimpleNamespace(analyze_email_attachments=AsyncMock(side_effect=RuntimeError("queue unavailable"))),
        raising=False,
    )
    assert await GmailEmailPersistence(session).store_emails(
        "owner", "account", [parsed()], gmail_service=object()
    ) == ["stored-email"]
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_database_failure_rolls_back_instead_of_using_previous_email():
    session = session_stub()
    session.execute.side_effect = SQLAlchemyError("database unavailable")
    prompts = SimpleNamespace(get_active_prompt=AsyncMock(return_value=SimpleNamespace(template="Prompt")))
    llm = SimpleNamespace(process_prompt=AsyncMock())
    with pytest.raises(SQLAlchemyError):
        await GmailAIProcessor(session, llm, prompts).process_emails_with_ai(["email"])
    session.rollback.assert_awaited_once()
    llm.process_prompt.assert_not_awaited()


@pytest.mark.asyncio
async def test_facade_parse_store_and_ai_pipeline(db_session, monkeypatch):
    import base64

    from app.services import gmail_ingestion_service

    llm = SimpleNamespace(process_prompt=AsyncMock(side_effect=["Work", "Summary"]))
    prompts = SimpleNamespace(get_active_prompt=AsyncMock(return_value=SimpleNamespace(template="Prompt")))
    monkeypatch.setattr(gmail_ingestion_service, "LLMService", lambda: llm)
    monkeypatch.setattr(gmail_ingestion_service, "PromptService", lambda db: prompts)
    owner = User(email="pipeline@example.com", password_hash="hash")
    db_session.add(owner)
    await db_session.flush()
    account = UserEmailAccount(
        user_id=owner.id,
        email=owner.email,
        provider="gmail",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com",
        encrypted_password="encrypted",
    )
    db_session.add(account)
    await db_session.commit()
    service = gmail_ingestion_service.GmailIngestionService(db_session)
    parsed_message = service.parse_gmail_message(
        {
            "id": "19abcdef123",
            "internalDate": "1705320000000",
            "payload": {
                "mimeType": "text/plain",
                "body": {"data": base64.urlsafe_b64encode(b"Pipeline body").decode()},
            },
        }
    )
    ids = await service.store_emails(owner.id, account.id, [parsed_message])
    assert len(ids) == 1
    assert await service.process_emails_with_ai(ids) == 1
    stored = (await db_session.execute(select(Email).where(Email.id == ids[0]))).scalar_one()
    assert stored.body_text == "Pipeline body" and stored.body_html == ""
    assert stored.uid == 1705320000000 and stored.processing_status == "completed"
    assert stored.ai_category == "Work" and stored.ai_summary == "Summary"
    assert await service.store_emails(owner.id, account.id, [parsed_message]) == []
