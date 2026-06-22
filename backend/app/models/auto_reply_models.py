"""
Auto-reply rules and away-mode models.

- AutoReplyRule: user-defined rules (category/sender match, priority, confidence, approval, auto-send).
- AwayModeSetting: per-user "away mode" + optional time windows (only process auto-reply when away).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.models.database import Base


class AutoReplyRule(Base):
    __tablename__ = "auto_reply_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)

    # Matching
    match_category = Column(String, nullable=True)
    match_sender = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)

    # AI customization
    instructions = Column(Text, nullable=True)

    # Upgrades: priority (lower = higher priority), confidence, away-mode, approval, auto-send
    priority = Column(Integer, default=0)
    confidence_min = Column(Float, default=0.0)
    require_away_mode = Column(Boolean, default=True)
    use_approval_queue = Column(Boolean, default=True)
    auto_send = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "match_category": self.match_category,
            "match_sender": self.match_sender,
            "is_active": self.is_active,
            "instructions": self.instructions,
            "priority": self.priority,
            "confidence_min": self.confidence_min,
            "require_away_mode": self.require_away_mode,
            "use_approval_queue": self.use_approval_queue,
            "auto_send": self.auto_send,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AwayModeSetting(Base):
    __tablename__ = "away_mode_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True, unique=True)

    is_active = Column(Boolean, default=False)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
