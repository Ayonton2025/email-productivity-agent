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


@pytest.mark.asyncio
async def test_user_listing_orders_received_at_and_filters_user(db_session):
    service = EmailService(db_session)
    for user, subject, timestamp in [
        ("user-1", "Older", "2026-01-01T00:00:00"),
        ("user-2", "Other user", "2026-01-04T00:00:00"),
        ("user-1", "Newer", "2026-01-03T00:00:00"),
    ]:
        await service.process_single_email(
            {"sender": "sender@example.test", "subject": subject, "timestamp": timestamp}, user
        )
    result = await service.get_user_emails("user-1", limit=1)
    assert [row["subject"] for row in result] == ["Newer"]
    assert [row["subject"] for row in await service.get_user_emails("user-1", offset=1)] == ["Older"]


@pytest.mark.asyncio
async def test_serialization_programming_error_propagates(db_session, monkeypatch):
    from app.models.database import Email

    service = EmailService(db_session)
    await service.process_single_email({"subject": "Broken serializer"}, "user-1")

    def broken(_self):
        raise AttributeError("serializer bug")

    monkeypatch.setattr(Email, "to_dict", broken)
    with pytest.raises(AttributeError, match="serializer bug"):
        await service.get_user_emails("user-1")


@pytest.mark.asyncio
async def test_rollback_failure_preserves_commit_error(db_session, monkeypatch):
    service = EmailService(db_session)
    failure = SQLAlchemyError("original commit failure")
    with monkeypatch.context() as patch:
        patch.setattr(service.db, "commit", AsyncMock(side_effect=failure))
        rollback = AsyncMock(side_effect=SQLAlchemyError("rollback failure"))
        patch.setattr(service.db, "rollback", rollback)
        with pytest.raises(EmailPersistenceError) as caught:
            await service.process_single_email({"subject": "Cannot save"}, "user-1")
        assert caught.value.__cause__ is failure
        rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_category_update_is_persisted(db_session):
    service = EmailService(db_session)
    email = await service.process_single_email({"subject": "Categorize"}, "user-1")
    assert await service.update_email_category(email["id"], "Important", "user-1")
    db_session.expire_all()
    updated = await service.get_email_by_id(email["id"], "user-1")
    assert updated["ai_category"] == "Important"


@pytest.mark.asyncio
async def test_failed_draft_write_rolls_back(db_session, monkeypatch):
    service = EmailService(db_session)
    failure = SQLAlchemyError("draft commit failed")
    monkeypatch.setattr(service.db, "commit", AsyncMock(side_effect=failure))
    rollback = AsyncMock(wraps=service.db.rollback)
    monkeypatch.setattr(service.db, "rollback", rollback)
    payload = {"subject": "Draft", "body": "Body", "metadata": {"origin": "test"}}
    with pytest.raises(EmailPersistenceError) as caught:
        await service.create_draft(payload, "user-1")
    assert caught.value.__cause__ is failure
    assert payload["metadata"] == {"origin": "test"}
    rollback.assert_awaited_once()
