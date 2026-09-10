"""Behavior checks across the extracted endpoint groups, without external calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.api import endpoints
from app.main import app
from app.models.database import get_db


def override_session(session):
    async def dependency():
        yield session

    app.dependency_overrides[get_db] = dependency


def test_drafts_are_created_for_authenticated_user(client, monkeypatch):
    create = AsyncMock(return_value={"id": "draft-1"})
    monkeypatch.setattr(endpoints.EmailService, "create_draft", create)
    response = client.post(
        "/api/v1/drafts", json={"subject": "Hello", "body": "Draft", "recipient": "test@example.com"}
    )
    assert response.status_code == 200
    assert response.json() == {"id": "draft-1"}
    assert create.await_args.kwargs == {"user_id": "test-user-id"}
    assert create.await_args.args[0]["recipient"] == "test@example.com"


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/drafts"),
        ("post", "/drafts"),
        ("get", "/email-accounts"),
        ("get", "/agent/status"),
        ("post", "/agent/process"),
    ],
)
def test_protected_groups_reject_missing_credentials(unauthenticated_client, method, path):
    response = unauthenticated_client.request(method, "/api/v1" + path)
    assert response.status_code in (401, 403)


def test_missing_email_preserves_404_and_user_scope(client, monkeypatch):
    query = AsyncMock(return_value=None)
    monkeypatch.setattr(endpoints.EmailService, "get_email_by_id", query)
    response = client.get("/api/v1/emails/missing")
    assert response.status_code == 404
    query.assert_awaited_once_with("missing", "test-user-id")


def test_prompt_update_preserves_partial_payload_and_404(client, monkeypatch):
    update = AsyncMock(return_value=None)
    monkeypatch.setattr(endpoints.PromptService, "update_prompt", update)
    response = client.put("/api/v1/prompts/missing", json={"name": "Renamed"})
    assert response.status_code == 404
    update.assert_awaited_once_with("missing", {"name": "Renamed"})


def test_account_listing_uses_authenticated_owner(client):
    result = Mock()
    result.scalars.return_value.all.return_value = [SimpleNamespace(to_dict=lambda: {"id": "account-1"})]
    session = SimpleNamespace(execute=AsyncMock(return_value=result))
    override_session(session)
    response = client.get("/api/v1/email-accounts")
    assert response.status_code == 200 and response.json() == [{"id": "account-1"}]
    statement = session.execute.await_args.args[0]
    assert "test-user-id" in statement.compile().params.values()


def test_reply_generation_retains_context_and_draft_ownership(client, monkeypatch):
    monkeypatch.setattr(
        endpoints.EmailService,
        "get_email_by_id",
        AsyncMock(return_value={"sender": "sender@example.test", "subject": "Question"}),
    )
    generate = AsyncMock(return_value={"body": "Answer", "ai_generated": True})
    create = AsyncMock(return_value={"id": "reply-draft"})
    monkeypatch.setattr(endpoints.EmailService, "generate_reply_draft", generate)
    monkeypatch.setattr(endpoints.EmailService, "create_draft", create)
    response = client.post("/api/v1/emails/email-1/generate-reply", json={})
    assert response.status_code == 200
    assert response.json()["reply"] == "Answer"
    assert response.json()["ai_generated"] is True
    assert generate.await_args.args == ("email-1", "test-user-id")
    assert generate.await_args.kwargs["user_plan"] == "professional"
    assert create.await_args.kwargs == {"user_id": "test-user-id"}
    assert create.await_args.args[0]["context_email_id"] == "email-1"


def test_agent_custom_prompt_is_forwarded(client, monkeypatch):
    monkeypatch.setattr(
        endpoints.EmailService,
        "get_email_by_id",
        AsyncMock(return_value={"sender": "sender@example.test", "subject": "Question", "body": "Content"}),
    )
    process = AsyncMock(return_value="Result")
    monkeypatch.setattr(endpoints.LLMService, "process_prompt", process)
    response = client.post(
        "/api/v1/agent/process", json={"email_id": "email-1", "prompt_type": "summary", "custom_prompt": "Summarize"}
    )
    assert response.status_code == 200
    assert response.json()["used_custom_prompt"] is True
    assert response.json()["result"] == "Result"
    assert process.await_args.args == ("Summarize", "From: sender@example.test\nSubject: Question\nBody: Content", None)


def test_health_and_info_routes(client, monkeypatch):
    override_session(SimpleNamespace(execute=AsyncMock()))
    monkeypatch.setattr(endpoints.LLMService, "health_check", AsyncMock(return_value={"status": "mock"}))
    assert client.get("/api/v1/health/db").json()["service"] == "db"
    assert client.get("/api/v1/health/ai").json() == {"status": "mock"}
    assert client.get("/api/v1/info").json()["name"] == "Bylix Email API"


def test_websocket_connect_dispatch_and_disconnect(client, monkeypatch):
    from app.api.websockets import manager

    async def connect(socket, client_id, db):
        await socket.accept()
        manager._test_socket = socket

    async def dispatch(client_id, data):
        await manager._test_socket.send_json({"client_id": client_id, "received": data})

    connect_mock = AsyncMock(side_effect=connect)
    dispatch_mock = AsyncMock(side_effect=dispatch)
    disconnect = Mock()
    monkeypatch.setattr(manager, "_test_socket", None, raising=False)
    monkeypatch.setattr(manager, "connect", connect_mock)
    monkeypatch.setattr(manager, "handle_websocket_message", dispatch_mock)
    monkeypatch.setattr(manager, "disconnect", disconnect)
    with client.websocket_connect("/api/v1/ws/agent?client_id=phase11") as socket:
        socket.send_json({"message": "hello"})
        assert socket.receive_json() == {"client_id": "phase11", "received": {"message": "hello"}}
    connect_mock.assert_awaited_once()
    dispatch_mock.assert_awaited_once_with("phase11", {"message": "hello"})
    disconnect.assert_called_once_with("phase11")
