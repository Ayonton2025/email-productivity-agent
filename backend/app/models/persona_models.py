"""
Persona profile models for tone/style customization.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey, Index

from app.models.database import Base


class PersonaProfile(Base):
    __tablename__ = "persona_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    tone = Column(String, default="professional")
    style = Column(String, default="clear")
    signature = Column(Text, nullable=True)
    emoji_level = Column(Integer, default=0)  # 0-5
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_persona_user_name", "user_id", "name", unique=True),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "tone": self.tone,
            "style": self.style,
            "signature": self.signature,
            "emoji_level": self.emoji_level,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
