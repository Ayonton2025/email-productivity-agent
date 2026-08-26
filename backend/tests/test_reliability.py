from pathlib import Path

from app.core import monitoring


def test_application_source_contains_no_print_calls():
    app_root = Path(__file__).resolve().parents[1] / "app"
    offenders = [
        str(path.relative_to(app_root))
        for path in app_root.rglob("*.py")
        if "print(" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_monitoring_is_disabled_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    assert monitoring.initialize_monitoring() is False


def test_capture_exception_is_noop_without_dsn(monkeypatch):
    monkeypatch.setattr(monitoring.settings, "SENTRY_DSN", None)
    monitoring.capture_exception(RuntimeError("expected test failure"), task="test")
