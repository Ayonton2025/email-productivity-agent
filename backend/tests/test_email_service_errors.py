from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import EmailDataLoadError, EmailPersistenceError
from app.services import email_service
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_mock_email_loading_wraps_database_errors(db_session, monkeypatch):
    service = EmailService(db_session)
    monkeypatch.setattr(service, "get_user_emails", AsyncMock(side_effect=SQLAlchemyError("database offline")))

    with pytest.raises(EmailPersistenceError):
        await service.load_mock_emails("user-1")


@pytest.mark.asyncio
async def test_mock_email_loading_wraps_unreadable_data_file(db_session, monkeypatch):
    service = EmailService(db_session)
    monkeypatch.setattr(service, "get_user_emails", AsyncMock(return_value=[]))
    monkeypatch.setattr(email_service.os.path, "exists", lambda path: path == "data/mock_inbox.json")

    def fail_open(*args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(email_service, "open", fail_open, raising=False)

    with pytest.raises(EmailDataLoadError):
        await service.load_mock_emails("user-1")