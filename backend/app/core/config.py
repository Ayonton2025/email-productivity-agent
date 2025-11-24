import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    APP_NAME: str = "Email Productivity Agent"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-here-make-it-very-long-and-secure-in-production"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./email_agent.db"
    
    # LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"  # openai, anthropic, or mock
    
    # Email Settings
    MOCK_DATA_PATH: str = "data/mock_inbox.json"
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback"
    
    class Config:
        env_file = ".env"

settings = Settings()
