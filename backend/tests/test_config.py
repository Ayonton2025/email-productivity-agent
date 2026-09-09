from pathlib import Path

from dotenv import dotenv_values

from app.core.config import Settings


def test_settings_parse_origins_and_keywords():
    settings = Settings(
        ALLOWED_ORIGINS=" http://a.test, ,http://b.test ", HOSTED_EMAIL_SPAM_KEYWORDS="Free Money, urgent offer"
    )
    assert settings.get_allowed_origins() == ["http://a.test", "http://b.test"]
    assert settings.get_hosted_spam_keywords() == ["free money", "urgent offer"]


def test_settings_resolve_provider_specific_credentials():
    settings = Settings(HOSTED_EMAIL_PROVIDER="mailu", MAILU_API_BASE_URL="https://mailu.test", MAILU_API_TOKEN="token")
    assert settings.get_hosted_provider_api_base() == "https://mailu.test"
    assert settings.get_hosted_provider_api_key() == "token"


def test_root_environment_template_is_complete_and_unambiguous():
    template = Path(__file__).resolve().parents[2] / ".env.example"
    assignments = [
        line.split("=", 1)[0]
        for line in template.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    ]
    assert len(assignments) == len(set(assignments)), "Duplicate settings silently override earlier values"
    values = dotenv_values(template)
    assert set(Settings.model_fields) <= values.keys()
    settings = Settings(**values)
    assert settings.ENABLE_MOCK_MODE is True
    assert settings.DATABASE_URL.startswith("sqlite+aiosqlite:")
    assert settings.CELERY_ENABLED is False
    assert settings.ENABLE_LIVE_FX_RATES is False
    assert settings.ENABLE_GEOIP_DETECTION is False
