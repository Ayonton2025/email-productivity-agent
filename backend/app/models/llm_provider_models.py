from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, JSON, Float, Index, ForeignKey

from app.models.database import Base


class LLMProviderConfig(Base):
    __tablename__ = "llm_provider_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=False)
    priority = Column(Integer, default=100, index=True)
    model = Column(String, nullable=True)
    endpoint = Column(String, nullable=True)
    api_keys_encrypted = Column(JSON, default=list)
    additional_headers = Column(JSON, default=dict)
    extra_config = Column(JSON, default=dict)
    max_retries = Column(Integer, default=2)
    backoff_seconds = Column(Float, default=0.8)
    timeout_seconds = Column(Integer, default=30)

    is_healthy = Column(Boolean, default=False)
    last_error = Column(Text, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)

    updated_by = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_llm_provider_priority_enabled", "is_enabled", "priority"),
    )

