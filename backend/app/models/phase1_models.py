"""
Phase 1 models:
- Daily AI briefings (cached daily digest)
- Follow-up policy and processing queue
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)

from app.models.database import Base


class UserDigestPreference(Base):
    __tablename__ = "user_digest_preferences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True, unique=True)
    timezone = Column(String, default="UTC", nullable=False)
    send_hour = Column(Integer, default=6, nullable=False)  # Local hour in user timezone
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "timezone": self.timezone,
            "send_hour": self.send_hour,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DailyBriefing(Base):
    __tablename__ = "daily_briefings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    briefing_date = Column(Date, nullable=False, index=True)
    content = Column(JSON, default=dict, nullable=False)  # Structured briefing payload
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    credits_used = Column(Integer, default=0, nullable=False)
    status = Column(String, default="generated", nullable=False)  # generated, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_daily_briefing_user_date", "user_id", "briefing_date", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "briefing_date": self.briefing_date.isoformat() if isinstance(self.briefing_date, date) else str(self.briefing_date),
            "content": self.content or {},
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "credits_used": self.credits_used,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class FollowUpPolicy(Base):
    __tablename__ = "follow_up_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True, unique=True)
    enabled = Column(Boolean, default=True, nullable=False)
    min_delay_hours = Column(Integer, default=48, nullable=False)
    max_stages = Column(Integer, default=3, nullable=False)
    auto_send = Column(Boolean, default=False, nullable=False)
    tone_profile = Column(String, default="professional", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "enabled": self.enabled,
            "min_delay_hours": self.min_delay_hours,
            "max_stages": self.max_stages,
            "auto_send": self.auto_send,
            "tone_profile": self.tone_profile,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class FollowUpExecution(Base):
    __tablename__ = "follow_up_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_email_id = Column(String, ForeignKey("emails.id"), nullable=False, index=True)
    draft_email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    stage = Column(Integer, default=1, nullable=False)
    scheduled_for = Column(DateTime, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending_approval", nullable=False, index=True)
    generated_subject = Column(String, nullable=True)
    generated_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_followup_user_status", "user_id", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_email_id": self.source_email_id,
            "draft_email_id": self.draft_email_id,
            "stage": self.stage,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "status": self.status,
            "generated_subject": self.generated_subject,
            "generated_body": self.generated_body,
            "error_message": self.error_message,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
