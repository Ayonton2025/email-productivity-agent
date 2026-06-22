import os
from typing import Optional, List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    APP_NAME: str = "Bylix Email"
    DEBUG: bool = False
    SECRET_KEY: str = ""
    ENCRYPTION_KEY: str = ""  # Must be 32 chars for AES-256
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./email_agent.db"
    
    # LLM Settings
    # Default to auto-select across configured providers (Admin LLM Ops).
    LLM_PROVIDER: str = "auto"
    LLM_MODEL: str = "gpt-4o-mini"
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None  # Legacy, kept for backwards compatibility
    ANTHROPIC_API_KEY: Optional[str] = None  # Legacy, kept for backwards compatibility
    # Additional LLM provider keys (add in .env, do not hardcode keys)
    HUGGINGFACE_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OLLAMA_URL: Optional[str] = None  # e.g., http://localhost:11434
    
    # Email Settings
    MOCK_DATA_PATH: str = "data/mock_inbox.json"
    
    # Email Sync Settings
    ENABLE_IMAP_IDLE: bool = True  # Use IMAP IDLE for real-time notifications
    EMAIL_SYNC_INTERVAL: int = 300  # Fallback polling interval in seconds (5 minutes)
    MAX_IMAP_CONNECTIONS_PER_USER: int = 1
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    
    # Outlook OAuth Settings
    OUTLOOK_CLIENT_ID: Optional[str] = None
    OUTLOOK_CLIENT_SECRET: Optional[str] = None
    OUTLOOK_TENANT_ID: Optional[str] = None
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"
    
    # CORS Settings
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # Server Settings
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Email Processing Settings
    MAX_EMAILS_PER_PAGE: int = 50
    EMAIL_SYNC_TIMEOUT: int = 300
    
    # AI Processing Settings
    MAX_TOKENS: int = 1000
    AI_TEMPERATURE: float = 0.3
    AI_TIMEOUT: int = 60
    WORKPLACE_ASSIST_MONTHLY_LIMIT: int = 100
    
    # Security Settings
    BCRYPT_ROUNDS: int = 12
    JWT_ALGORITHM: str = "HS256"
    
    # Feature Flags
    ENABLE_EMAIL_SYNC: bool = True
    ENABLE_AI_PROCESSING: bool = True
    ENABLE_MOCK_MODE: bool = True
    
    # Analytics Settings
    ENABLE_ANALYTICS: bool = True
    ANALYTICS_RETENTION_DAYS: int = 90
    
    # Billing & Payment Settings
    # Paystack (Primary - Africa)
    PAYSTACK_API_KEY: Optional[str] = None
    PAYSTACK_SECRET_KEY: Optional[str] = None
    PAYSTACK_PUBLIC_KEY: Optional[str] = None
    PAYSTACK_API_BASE_URL: str = "https://api.paystack.co"
    PAYSTACK_SUPPORTED_CURRENCIES: str = "NGN"  # Comma-separated, e.g. NGN,GHS,ZAR,KES,USD
    PAYSTACK_FALLBACK_CURRENCY: str = "NGN"
    PAYSTACK_FORCE_CURRENCY: Optional[str] = None  # Optional forced settlement currency for Paystack
    BILLING_CHARGE_CURRENCY: str = "USD"  # canonical price currency for website plans
    BILLING_STRICT_USD: bool = True  # if true, price source remains USD and local conversion is explicit
    BILLING_FX_BUFFER_PERCENT: float = 0.0  # Optional buffer (e.g., 2.0 => +2%)
    ENABLE_LIVE_FX_RATES: bool = True
    FX_RATE_API_BASE_URL: str = "https://api.exchangerate.host"
    FX_RATE_API_KEY: Optional[str] = None
    FX_RATE_CACHE_MINUTES: int = 15
    ENABLE_GEOIP_DETECTION: bool = True
    GEOIP_API_BASE_URL: str = "https://ipapi.co"
    
    # PayPal (Global Fallback)
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"  # sandbox or live
    PAYPAL_API_BASE_URL: str = "https://api-m.sandbox.paypal.com"  # Sandbox by default
    PAYPAL_API_BASE_URL_LIVE: str = "https://api-m.paypal.com"

    # Coinbase Commerce (Crypto payments)
    COINBASE_COMMERCE_API_KEY: Optional[str] = None
    COINBASE_COMMERCE_API_BASE: str = "https://api.commerce.coinbase.com"

    # Bybit Pay (Crypto payments)
    BYBIT_PAY_API_KEY: Optional[str] = None
    BYBIT_PAY_API_SECRET: Optional[str] = None
    BYBIT_PAY_MERCHANT_ID: Optional[str] = None
    BYBIT_PAY_API_BASE: str = "https://api.bybit.com"

    # Stripe (optional)
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Task Queue Settings (Celery)
    # Default to the Docker service name 'redis' so Celery connects correctly inside Compose
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLED: bool = True
    
    # Email Sending Settings (for campaigns)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True

    # Hosted/Internal Email (Option A) Settings
    HOSTED_EMAIL_ENABLED: bool = False
    HOSTED_EMAIL_PROVIDER: str = "mock"  # mock, mailcow, postal, mailu, resend, sendgrid
    HOSTED_EMAIL_DOMAIN: Optional[str] = None  # e.g. bylix.email
    HOSTED_EMAIL_ALLOW_PUBLIC_SIGNUP: bool = False
    HOSTED_EMAIL_DEFAULT_PASSWORD_LENGTH: int = 24
    HOSTED_EMAIL_MAILBOX_QUOTA_MB: int = 1024

    # Hosted mailbox IMAP/SMTP values (used by internal account abstraction)
    HOSTED_EMAIL_IMAP_HOST: Optional[str] = None
    HOSTED_EMAIL_IMAP_PORT: int = 993
    HOSTED_EMAIL_SMTP_HOST: Optional[str] = None
    HOSTED_EMAIL_SMTP_PORT: int = 587
    HOSTED_EMAIL_USE_TLS: bool = True

    # Hosted provider API credentials
    HOSTED_EMAIL_API_BASE_URL: Optional[str] = None
    HOSTED_EMAIL_API_KEY: Optional[str] = None
    HOSTED_EMAIL_API_TIMEOUT_SECONDS: int = 20

    # Provider-specific API credentials (preferred where applicable)
    MAILCOW_API_BASE_URL: Optional[str] = None
    MAILCOW_API_KEY: Optional[str] = None
    POSTAL_API_BASE_URL: Optional[str] = None
    POSTAL_API_KEY: Optional[str] = None
    MAILU_API_BASE_URL: Optional[str] = None
    MAILU_API_TOKEN: Optional[str] = None
    RESEND_API_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    ADMIN_EMAILS: str = ""

    # Abuse prevention
    HOSTED_EMAIL_DAILY_SEND_LIMIT: int = 200
    HOSTED_EMAIL_DOMAIN_DAILY_SEND_LIMIT: int = 5000
    HOSTED_EMAIL_MAX_LINKS_PER_EMAIL: int = 8
    HOSTED_EMAIL_MAX_RECIPIENTS_PER_DAY: int = 200
    HOSTED_EMAIL_SPAM_SCORE_BLOCK_THRESHOLD: float = 0.75
    HOSTED_EMAIL_ABUSE_USE_AI: bool = False
    HOSTED_EMAIL_SPAM_KEYWORDS: str = "free money,guaranteed income,click now,act now,urgent offer,crypto giveaway"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def get_allowed_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into list"""
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    def is_google_configured(self) -> bool:
        """Check if Google Gemini is properly configured"""
        return bool(self.GOOGLE_API_KEY)

    def is_openai_configured(self) -> bool:
        """Check if OpenAI is properly configured"""
        return bool(self.OPENAI_API_KEY)

    def is_anthropic_configured(self) -> bool:
        """Check if Anthropic is properly configured"""
        return bool(self.ANTHROPIC_API_KEY)

    def is_huggingface_configured(self) -> bool:
        return bool(self.HUGGINGFACE_API_KEY)

    def is_openrouter_configured(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    def is_ollama_configured(self) -> bool:
        return bool(self.OLLAMA_URL)

    def is_llm_configured(self) -> bool:
        """Check if any LLM provider is configured"""
        return (
            self.is_google_configured()
            or self.is_openai_configured()
            or self.is_anthropic_configured()
            or self.is_huggingface_configured()
            or self.is_openrouter_configured()
            or self.is_ollama_configured()
        )

    def get_llm_config(self) -> dict:
        """Get LLM configuration as dictionary"""
        return {
            "provider": self.LLM_PROVIDER,
            "model": self.LLM_MODEL,
            "google_configured": self.is_google_configured(),
            "openai_configured": self.is_openai_configured(),
            "anthropic_configured": self.is_anthropic_configured(),
            "mock_mode": not self.is_llm_configured()
        }

    def get_oauth_config(self) -> dict:
        """Get OAuth configuration as dictionary"""
        return {
            "google_configured": bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET),
            "outlook_configured": bool(self.OUTLOOK_CLIENT_ID and self.OUTLOOK_CLIENT_SECRET),
            "google_redirect_uri": self.GOOGLE_REDIRECT_URI
        }

    def get_provider_config(self, domain: str) -> Optional[dict]:
        """Get IMAP/SMTP configuration for email provider by domain"""
        provider_configs = {
            "gmail.com": {
                "name": "Gmail",
                "imap_host": "imap.gmail.com",
                "imap_port": 993,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "requires_app_password": True
            },
            "yahoo.com": {
                "name": "Yahoo",
                "imap_host": "imap.mail.yahoo.com",
                "imap_port": 993,
                "smtp_host": "smtp.mail.yahoo.com",
                "smtp_port": 587,
                "use_tls": True,
                "requires_app_password": True
            },
            "outlook.com": {
                "name": "Outlook",
                "imap_host": "imap-mail.outlook.com",
                "imap_port": 993,
                "smtp_host": "smtp-mail.outlook.com",
                "smtp_port": 587,
                "use_tls": True,
                "requires_app_password": False
            },
            "hotmail.com": {
                "name": "Hotmail",
                "imap_host": "imap-mail.outlook.com",
                "imap_port": 993,
                "smtp_host": "smtp-mail.outlook.com",
                "smtp_port": 587,
                "use_tls": True,
                "requires_app_password": False
            }
        }
        
        # Try exact domain match first
        if domain in provider_configs:
            return provider_configs[domain]
        
        # Try partial match (e.g., "company.gmail.com" -> "gmail.com")
        for key, config in provider_configs.items():
            if domain.endswith("." + key) or domain.endswith(key):
                return config
        
        return None

    def get_hosted_spam_keywords(self) -> List[str]:
        """Parse hosted email spam keywords from env."""
        raw = self.HOSTED_EMAIL_SPAM_KEYWORDS or ""
        return [kw.strip().lower() for kw in raw.split(",") if kw.strip()]

    def get_hosted_provider_api_base(self) -> Optional[str]:
        """
        Resolve provider base URL with provider-specific vars taking precedence.
        """
        provider = (self.HOSTED_EMAIL_PROVIDER or "").strip().lower()
        if provider == "mailcow":
            return self.MAILCOW_API_BASE_URL or self.HOSTED_EMAIL_API_BASE_URL
        if provider == "postal":
            return self.POSTAL_API_BASE_URL or self.HOSTED_EMAIL_API_BASE_URL
        if provider == "mailu":
            return self.MAILU_API_BASE_URL or self.HOSTED_EMAIL_API_BASE_URL
        return self.HOSTED_EMAIL_API_BASE_URL

    def get_hosted_provider_api_key(self) -> Optional[str]:
        """
        Resolve provider API key/token with provider-specific vars taking precedence.
        """
        provider = (self.HOSTED_EMAIL_PROVIDER or "").strip().lower()
        if provider == "mailcow":
            return self.MAILCOW_API_KEY or self.HOSTED_EMAIL_API_KEY
        if provider == "postal":
            return self.POSTAL_API_KEY or self.HOSTED_EMAIL_API_KEY
        if provider == "mailu":
            return self.MAILU_API_TOKEN or self.HOSTED_EMAIL_API_KEY
        if provider == "resend":
            return self.RESEND_API_KEY or self.HOSTED_EMAIL_API_KEY
        if provider == "sendgrid":
            return self.SENDGRID_API_KEY or self.HOSTED_EMAIL_API_KEY
        return self.HOSTED_EMAIL_API_KEY

    def validate_critical_secrets(self) -> List[str]:
        """Return configuration issues for required security secrets."""
        issues: List[str] = []

        secret = (self.SECRET_KEY or "").strip()
        encryption = (self.ENCRYPTION_KEY or "").strip()

        if not secret:
            issues.append("SECRET_KEY is missing")
        elif len(secret) < 32:
            issues.append("SECRET_KEY must be at least 32 characters")
        elif "change-this" in secret.lower() or "super-secret" in secret.lower():
            issues.append("SECRET_KEY uses a placeholder/default-like value")

        if not encryption:
            issues.append("ENCRYPTION_KEY is missing")
        elif len(encryption) < 32:
            issues.append("ENCRYPTION_KEY must be at least 32 characters")
        elif "change-this" in encryption.lower():
            issues.append("ENCRYPTION_KEY uses a placeholder/default-like value")

        return issues

# Global settings instance
settings = Settings()
