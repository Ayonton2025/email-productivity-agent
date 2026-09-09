import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.api import endpoints
from app.main import app
from app.models.database import get_db

URL = "/api/v1/emails/my-inbox"
PRIVATE = "private-body subject recipient@example.com oauth-secret password-secret attachment-secret"


def test_inbox_service_failure_is_500_and_logs_safe_context(client, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    query = AsyncMock(side_effect=RuntimeError(PRIVATE))
    monkeypatch.setattr(endpoints.EmailService, "get_user_emails", query)
    response = client.get(URL, headers={"X-Request-ID": "inbox-error-123"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to retrieve inbox"}
    assert response.json() != []
    assert response.headers["X-Request-ID"] == "inbox-error-123"
    records = [r for r in caplog.records if r.name == endpoints.__name__]
    rendered = " ".join(r.getMessage() for r in records)
    assert "get_user_inbox_failed" in rendered
    assert "test-user-id" in rendered and "inbox-error-123" in rendered
    assert "RuntimeError" in rendered and "duration_ms" in rendered
    assert PRIVATE not in caplog.text
    assert all(r.exc_info is None for r in records)


def test_database_error_does_not_leak_through_service_logs(client, caplog):
    caplog.set_level(logging.INFO)
    session = SimpleNamespace(execute=AsyncMock(side_effect=SQLAlchemyError(PRIVATE)))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    response = client.get(URL)
    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to retrieve inbox"
    assert "email_list_query_failed" in caplog.text
    assert "SQLAlchemyError" in caplog.text
    assert "EmailPersistenceError" in caplog.text
    assert PRIVATE not in caplog.text and PRIVATE not in response.text
    assert all(r.exc_info is None for r in caplog.records)


def test_empty_inbox_remains_success(client, monkeypatch):
    query = AsyncMock(return_value=[])
    monkeypatch.setattr(endpoints.EmailService, "get_user_emails", query)
    response = client.get(URL)
    assert response.status_code == 200 and response.json() == []
    query.assert_awaited_once_with(user_id="test-user-id", limit=50, offset=0)


@pytest.mark.parametrize("sort_by, expected", [("newest", ["b", "a"]), ("oldest", ["a", "b"]), ("sender", ["b", "a"])])
def test_inbox_sorting_and_pagination_forwarding(client, monkeypatch, sort_by, expected):
    rows = [
        dict(id="a", sender="z@example.com", timestamp="2026-01-01"),
        dict(id="b", sender="a@example.com", timestamp="2026-01-02"),
    ]
    query = AsyncMock(return_value=rows)
    monkeypatch.setattr(endpoints.EmailService, "get_user_emails", query)
    response = client.get(URL, params=dict(sort_by=sort_by, limit=2, offset=3))
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == expected
    query.assert_awaited_once_with(user_id="test-user-id", limit=2, offset=3)


def test_inbox_filters_and_success_logs_exclude_content(client, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    rows = [
        dict(
            id="a", category="work", subject=PRIVATE, sender="sender@example.com", body="Review", timestamp="2026-01-01"
        ),
        dict(id="b", category="other", subject=PRIVATE, timestamp="2026-01-02"),
    ]
    monkeypatch.setattr(endpoints.EmailService, "get_user_emails", AsyncMock(return_value=rows))
    response = client.get(
        URL, params=dict(category="work", search="PRIVATE-BODY"), headers={"X-Request-ID": "inbox-success-123"}
    )
    assert response.status_code == 200
    assert response.json() == [rows[0]]
    assert "inbox_fetch_completed" in caplog.text
    assert "result_count" in caplog.text and "fetched_count" in caplog.text
    assert "inbox-success-123" in caplog.text
    assert PRIVATE not in caplog.text and "PRIVATE-BODY" not in caplog.text
    assert "sender@example.com" not in caplog.text


def test_inbox_requires_authentication(unauthenticated_client, monkeypatch):
    query = AsyncMock(return_value=[])
    monkeypatch.setattr(endpoints.EmailService, "get_user_emails", query)
    assert unauthenticated_client.get(URL).status_code in {401, 403}
    query.assert_not_awaited()
