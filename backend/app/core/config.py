import os
from typing import Optional, List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    APP_NAME: str = "Email Productivity Agent"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production-make-it-very-long-and-secure"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./email_agent.db"
    
    # LLM Settings
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-3.5-turbo"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Email Settings
    MOCK_DATA_PATH: str = "data/mock_inbox.json"
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    
    # Outlook OAuth Settings
    OUTLOOK_CLIENT_ID: Optional[str] = None
    OUTLOOK_CLIENT_SECRET: Optional[str] = None
    OUTLOOK_TENANT_ID: Optional[str] = None
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def get_allowed_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into list"""
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    def is_openai_configured(self) -> bool:
        """Check if OpenAI is properly configured"""
        return bool(self.OPENAI_API_KEY and self.LLM_PROVIDER == "openai")

    def is_anthropic_configured(self) -> bool:
        """Check if Anthropic is properly configured"""
        return bool(self.ANTHROPIC_API_KEY and self.LLM_PROVIDER == "anthropic")

    def is_llm_configured(self) -> bool:
        """Check if any LLM provider is configured"""
        return self.is_openai_configured() or self.is_anthropic_configured()

    def get_llm_config(self) -> dict:
        """Get LLM configuration as dictionary"""
        return {
            "provider": self.LLM_PROVIDER,
            "model": self.LLM_MODEL,
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

# Global settings instance
settings = Settings()
