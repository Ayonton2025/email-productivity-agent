from pathlib import Path

from app.main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent


def test_main_stays_below_phase_four_limit():
    assert len((BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8").splitlines()) < 300


def test_billing_modules_stay_focused():
    billing_dir = BACKEND_ROOT / "app" / "services" / "billing"
    oversized = {
        path.name: len(path.read_text(encoding="utf-8").splitlines())
        for path in billing_dir.glob("*.py")
        if len(path.read_text(encoding="utf-8").splitlines()) >= 500
    }
    assert oversized == {}


def test_phase_three_service_and_frontend_modules_stay_focused():
    paths = [
        BACKEND_ROOT / "app" / "services" / "llm_orchestration_service.py",
        BACKEND_ROOT / "app" / "services" / "model_registry.py",
        BACKEND_ROOT / "app" / "services" / "prompt_registry.py",
        BACKEND_ROOT / "app" / "services" / "llm_provider_mixin.py",
        BACKEND_ROOT / "app" / "services" / "llm_feature_mixin.py",
        REPOSITORY_ROOT / "frontend" / "src" / "App.jsx",
        REPOSITORY_ROOT / "frontend" / "src" / "routes.jsx",
        REPOSITORY_ROOT / "frontend" / "src" / "navigation.js",
        REPOSITORY_ROOT / "frontend" / "src" / "components" / "layout" / "SidebarContent.jsx",
    ]
    oversized = {
        str(path.relative_to(REPOSITORY_ROOT)): len(path.read_text(encoding="utf-8").splitlines())
        for path in paths
        if len(path.read_text(encoding="utf-8").splitlines()) >= 500
    }
    assert oversized == {}


def test_split_billing_routes_are_all_registered():
    paths = [path for path in app.openapi()["paths"] if path.startswith("/api/v1/billing")]
    assert len(paths) == 21
    assert len(paths) == len(set(paths))
    assert "/api/v1/billing/subscription" in paths
    assert "/api/v1/billing/webhook/paystack" in paths


def test_split_email_account_routes_are_all_registered():
    paths = [path for path in app.openapi()["paths"] if path.startswith("/api/v1/email-accounts")]
    assert len(paths) == 16
    assert "/api/v1/email-accounts/gmail/auth-url" in paths
    assert "/api/v1/email-accounts/{account_id}/send" in paths
