"""
Collaboration models for shared inbox functionality.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text

from app.models.database import Base


class SharedInbox(Base):
    __tablename__ = "shared_inboxes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_user_id": self.owner_user_id,
            "name": self.name,
            "description": self.description,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SharedInboxMember(Base):
    __tablename__ = "shared_inbox_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    inbox_id = Column(String, ForeignKey("shared_inboxes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, default="member")  # owner, admin, member
    joined_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_shared_inbox_member_unique", "inbox_id", "user_id", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "inbox_id": self.inbox_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class SharedInboxEmail(Base):
    __tablename__ = "shared_inbox_emails"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    inbox_id = Column(String, ForeignKey("shared_inboxes.id", ondelete="CASCADE"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)
    added_by_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="open", index=True)  # open, in_progress, resolved
    assigned_to_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_shared_inbox_email_unique", "inbox_id", "email_id", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "inbox_id": self.inbox_id,
            "email_id": self.email_id,
            "added_by_user_id": self.added_by_user_id,
            "status": self.status,
            "assigned_to_user_id": self.assigned_to_user_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
