from fastapi.testclient import TestClient

from app.core import monitoring
from app.core.config import settings
from app.main import app


def test_monitoring_disabled_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    assert monitoring.initialize_monitoring() is False


def test_capture_exception_is_safe_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    monitoring.capture_exception(RuntimeError("handled"), operation="test")


def test_debug_error_endpoint_is_hidden_when_debug_disabled(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    with TestClient(app) as client:
        response = client.get("/debug/error")
    assert response.status_code == 404


def test_debug_error_endpoint_raises_when_debug_enabled(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/debug/error")
    assert response.status_code == 500
