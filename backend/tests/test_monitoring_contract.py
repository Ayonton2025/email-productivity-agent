import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import sentry_sdk
from fastapi.testclient import TestClient

from app.core import monitoring
from app.core.config import settings
from app.main import app


def test_monitoring_disabled_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    initialize = MagicMock()
    monkeypatch.setattr(sentry_sdk, "init", initialize)
    assert monitoring.initialize_monitoring() is False
    initialize.assert_not_called()


def test_capture_exception_is_safe_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    capture = MagicMock()
    monkeypatch.setattr(sentry_sdk, "capture_exception", capture)
    monitoring.capture_exception(RuntimeError("handled"), operation="test")
    capture.assert_not_called()


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


def test_monitoring_enabled_configuration(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setattr(settings, "ENVIRONMENT", "monitoring-test")
    monkeypatch.setattr(settings, "APP_VERSION", "phase7-test")
    monkeypatch.setattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.25)
    initialize = MagicMock()
    monkeypatch.setattr(sentry_sdk, "init", initialize)
    assert monitoring.initialize_monitoring() is True
    initialize.assert_called_once()
    options = initialize.call_args.kwargs
    assert options["dsn"] == "https://public@example.invalid/1"
    assert options["environment"] == "monitoring-test"
    assert options["release"] == "phase7-test"
    assert options["traces_sample_rate"] == 0.25
    assert options["send_default_pii"] is False
    assert {integration.identifier for integration in options["integrations"]} == {
        "fastapi",
        "celery",
        "sqlalchemy",
        "logging",
    }


def test_handled_exception_is_forwarded_with_scoped_context(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://public@example.invalid/1")
    scope_context = MagicMock()
    capture = MagicMock()
    monkeypatch.setattr(sentry_sdk, "push_scope", scope_context)
    monkeypatch.setattr(sentry_sdk, "capture_exception", capture)
    error = RuntimeError("controlled failure")
    monitoring.capture_exception(error, operation="phase7-check", user_id="test-user")
    scope_context.assert_called_once_with()
    scope = scope_context.return_value.__enter__.return_value
    scope.set_extra.assert_any_call("operation", "phase7-check")
    scope.set_extra.assert_any_call("user_id", "test-user")
    capture.assert_called_once_with(error)
    scope_context.return_value.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
def test_main_monitoring_wiring_in_fresh_process(enabled):
    # A subprocess contains the SDK's global integrations. An in-memory transport
    # prevents telemetry from leaving the process, including debug-route errors.
    code = r"""
import sys
import sentry_sdk
from sentry_sdk.transport import Transport

captured = []
initializations = []
class MemoryTransport(Transport):
    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.type == "event":
                captured.append(item.payload.json)

original_init = sentry_sdk.init
def initialize(*args, **kwargs):
    initializations.append(kwargs.copy())
    kwargs["transport"] = MemoryTransport
    kwargs["auto_session_tracking"] = False
    return original_init(*args, **kwargs)
sentry_sdk.init = initialize

from app.core import monitoring
bootstrap_callers = []
original_monitoring = monitoring.initialize_monitoring
def initialize_monitoring():
    bootstrap_callers.append(sys._getframe(1).f_globals.get("__name__"))
    return original_monitoring()
monitoring.initialize_monitoring = initialize_monitoring

from app.main import app
from fastapi.testclient import TestClient

enabled = sys.argv[1] == "enabled"
assert "app.main" in bootstrap_callers, bootstrap_callers
assert len(initializations) == (len(bootstrap_callers) if enabled else 0), initializations
if enabled:
    assert all(options["send_default_pii"] is False for options in initializations)
    assert all(options["traces_sample_rate"] == 0.0 for options in initializations)
    assert "fastapi" in sentry_sdk.get_client().integrations
assert "/debug/error" not in app.openapi()["paths"]
client = TestClient(app, raise_server_exceptions=False)
try:
    response = client.get("/debug/error")
    assert response.status_code == 500, response.text
    monitoring.capture_exception(RuntimeError("phase7-handled"), operation="phase7-check")
    sentry_sdk.flush(timeout=2)
    values = [value for event in captured for value in event.get("exception", {}).get("values", [])]
    if enabled:
        assert any(value.get("value") == "Intentional Sentry test exception" for value in values), values
        handled = next(event for event in captured if any(value.get("value") == "phase7-handled" for value in event.get("exception", {}).get("values", [])))
        assert handled["extra"]["operation"] == "phase7-check"
        assert "phase7-check" not in str([event for event in captured if event is not handled])
    else:
        assert not captured
finally:
    client.close()
    sentry_sdk.get_client().close(timeout=2)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, "enabled" if enabled else "disabled"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "SENTRY_DSN": "https://public@example.invalid/1" if enabled else "",
            "SENTRY_TRACES_SAMPLE_RATE": "0",
            "DEBUG": "true",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
