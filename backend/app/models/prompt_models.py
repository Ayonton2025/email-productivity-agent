"""Prompt template persistence."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.models.base import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # NULL for system prompts
    name = Column(String, nullable=False)
    description = Column(Text)
    template = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System prompts cannot be modified
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    prompt_metadata = Column(JSON, default=dict)

    # Add unique constraint for user-specific prompts
    __table_args__ = (Index("ix_prompts_user_name", "user_id", "name", unique=True),)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "category": self.category,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.prompt_metadata or {},
        }
