from app.core import monitoring


def test_monitoring_disabled_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    assert monitoring.initialize_monitoring() is False


def test_capture_exception_is_safe_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    monitoring.capture_exception(RuntimeError("handled"), operation="test")
