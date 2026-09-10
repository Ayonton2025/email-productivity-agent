import asyncio
import logging
from types import SimpleNamespace

import pytest
import structlog
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api import auth_endpoints
from app.core import security
from app.core.logging import get_logger
from app.core.request_logging import register_request_logging
from app.main import app
from app.models.database import get_db


def test_request_logging_returns_correlation_id():
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "request-test-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-test-123"


def test_request_logging_generates_correlation_id():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 36


def test_request_id_is_bound_during_request():
    @app.get("/_test/request-log", include_in_schema=False)
    async def request_log():
        return structlog.contextvars.get_contextvars()

    with TestClient(app) as client:
        response = client.get("/_test/request-log", headers={"X-Request-ID": "bound-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "bound-123"
    assert response.json()["request_id"] == "bound-123"


# Exercise the real authentication dependency in a small app, without provider or
# database traffic, while using the production logging middleware and processors.
@pytest.fixture(params=[security.get_current_user, auth_endpoints.get_current_user], ids=["core-auth", "account-auth"])
def authenticated_logging_app(caplog, request):
    caplog.set_level(logging.INFO)
    application = FastAPI()
    register_request_logging(application)
    users = {
        "alice": SimpleNamespace(id="alice", email="alice@example.com", is_active=True),
        "bob": SimpleNamespace(id="bob", email="bob@example.com", is_active=True),
        "inactive": SimpleNamespace(id="inactive", email="inactive@example.com", is_active=False),
    }

    async def execute(statement):
        user = users.get(statement.compile().params["id_1"])
        return SimpleNamespace(scalar_one_or_none=lambda: user)

    async def database():
        yield SimpleNamespace(execute=execute)

    application.dependency_overrides[security._lazy_get_db] = database
    application.dependency_overrides[get_db] = database
    log = get_logger("phase6.test")

    @application.get("/private")
    async def private(user=Depends(request.param)):
        await asyncio.sleep(0)
        log.info("downstream_service_event")
        return structlog.contextvars.get_contextvars()

    @application.get("/public")
    async def public():
        log.info("public_service_event")
        return structlog.contextvars.get_contextvars()

    @application.get("/failure")
    async def failure(user=Depends(request.param)):
        raise RuntimeError("controlled failure")

    return application


def auth_headers(user_id, request_id):
    return {
        "Authorization": "Bearer " + security.create_access_token({"user_id": user_id}),
        "X-Request-ID": request_id,
    }


def events(caplog, event):
    return [
        record.msg for record in caplog.records if isinstance(record.msg, dict) and record.msg.get("event") == event
    ]


def test_authenticated_logs_include_verified_user_and_request(authenticated_logging_app, caplog):
    with TestClient(authenticated_logging_app) as client:
        response = client.get("/private", headers=auth_headers("alice", "alice-request"))
    assert response.status_code == 200
    assert response.json() == {"user_id": "alice", "request_id": "alice-request"}
    for event in ("downstream_service_event", "http_request_completed"):
        record = events(caplog, event)[-1]
        assert record["user_id"] == "alice" and record["request_id"] == "alice-request"
    assert not structlog.contextvars.get_contextvars()


@pytest.mark.parametrize("identity", ["invalid-token", "missing", "inactive"])
def test_rejected_authentication_does_not_bind_user(authenticated_logging_app, caplog, identity):
    headers = auth_headers(identity, "rejected-request")
    if identity == "invalid-token":
        headers["Authorization"] = "Bearer invalid-token"
    with TestClient(authenticated_logging_app) as client:
        response = client.get("/private", headers=headers)
    assert response.status_code == 401
    assert not events(caplog, "downstream_service_event")
    record = events(caplog, "http_request_completed")[-1]
    assert "user_id" not in record and record["request_id"] == "rejected-request"


def test_user_context_does_not_leak_to_next_request(authenticated_logging_app, caplog):
    with TestClient(authenticated_logging_app) as client:
        assert client.get("/private", headers=auth_headers("alice", "first")).status_code == 200
        response = client.get("/public", headers={"X-Request-ID": "second", "X-User-ID": "spoofed"})
        rejected = client.get("/private", headers={"X-Request-ID": "third"})
    assert response.json() == {"request_id": "second"}
    assert rejected.status_code in {401, 403}
    records = events(caplog, "http_request_completed")
    assert records[0]["user_id"] == "alice"
    assert all("user_id" not in record for record in records[1:])
    assert not structlog.contextvars.get_contextvars()


def test_failed_request_logs_verified_identity_and_cleans_context(authenticated_logging_app, caplog):
    with TestClient(authenticated_logging_app, raise_server_exceptions=False) as client:
        response = client.get("/failure", headers=auth_headers("bob", "failed-request"))
        public = client.get("/public", headers={"X-Request-ID": "after-failure"})
    assert response.status_code == 500
    record = events(caplog, "http_request_failed")[-1]
    assert record["user_id"] == "bob" and record["request_id"] == "failed-request"
    assert public.json() == {"request_id": "after-failure"}
    assert not structlog.contextvars.get_contextvars()


@pytest.mark.asyncio
async def test_concurrent_requests_keep_separate_user_context(authenticated_logging_app, caplog):
    async with AsyncClient(transport=ASGITransport(app=authenticated_logging_app), base_url="http://test") as client:
        responses = await asyncio.gather(
            client.get("/private", headers=auth_headers("alice", "concurrent-alice")),
            client.get("/private", headers=auth_headers("bob", "concurrent-bob")),
            client.get("/public", headers={"X-Request-ID": "concurrent-public"}),
        )
    assert all(response.status_code == 200 for response in responses)
    assert [response.json() for response in responses] == [
        {"user_id": "alice", "request_id": "concurrent-alice"},
        {"user_id": "bob", "request_id": "concurrent-bob"},
        {"request_id": "concurrent-public"},
    ]
    for record in events(caplog, "downstream_service_event") + events(caplog, "http_request_completed"):
        expected = {"concurrent-alice": "alice", "concurrent-bob": "bob"}.get(record["request_id"])
        assert record.get("user_id") == expected
    assert not structlog.contextvars.get_contextvars()
