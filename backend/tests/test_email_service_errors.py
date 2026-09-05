from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import EmailDataLoadError, EmailPersistenceError
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_mock_email_loading_wraps_database_errors(db_session, monkeypatch):
    service = EmailService(db_session)
    monkeypatch.setattr(service, "get_user_emails", AsyncMock(side_effect=SQLAlchemyError("database offline")))

    with pytest.raises(EmailPersistenceError):
        await service.load_mock_emails("user-1")


@pytest.mark.asyncio
async def test_email_query_failure_becomes_persistence_error(db_session, monkeypatch):
    service = EmailService(db_session)
    monkeypatch.setattr(service.db, "execute", AsyncMock(side_effect=SQLAlchemyError("query failed")))

    with pytest.raises(EmailPersistenceError):
        await service.get_all_emails()


@pytest.mark.asyncio
async def test_email_commit_failure_becomes_persistence_error(db_session, monkeypatch):
    service = EmailService(db_session)
    monkeypatch.setattr(service.db, "commit", AsyncMock(side_effect=SQLAlchemyError("commit failed")))

    with pytest.raises(EmailPersistenceError):
        await service.process_single_email(
            {
                "sender": "sender@example.test",
                "subject": "Commit failure",
                "body": "This should not persist.",
                "timestamp": "2026-01-02T03:04:05Z",
            },
            "user-1",
        )


@pytest.mark.asyncio
async def test_programming_errors_are_not_masked(db_session, monkeypatch):
    service = EmailService(db_session)
    monkeypatch.setattr(service, "get_user_emails", AsyncMock(side_effect=KeyError("unexpected field")))

    with pytest.raises(KeyError, match="unexpected field"):
        await service.load_mock_emails("user-1")


@pytest.mark.asyncio
async def test_mock_email_loading_wraps_unreadable_data_file(db_session, monkeypatch):
    service = EmailService(db_session)
    monkeypatch.setattr(service, "get_user_emails", AsyncMock(return_value=[]))
    monkeypatch.setattr("app.services.mock_email_loader.os.path.exists", lambda path: path == "data/mock_inbox.json")

    def fail_open(*args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr("app.services.mock_email_loader.open", fail_open, raising=False)

    with pytest.raises(EmailDataLoadError):
        await service.load_mock_emails("user-1")
