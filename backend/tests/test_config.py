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
