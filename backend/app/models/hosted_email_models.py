"""
Hosted/internal email support models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, JSON

from app.models.database import Base


class HostedMailboxProvisioning(Base):
    __tablename__ = "hosted_mailbox_provisioning"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(String, ForeignKey("user_email_accounts.id"), nullable=True, index=True)
    email = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False)
    status = Column(String, default="requested", index=True)  # requested, provisioned, failed
    external_reference = Column(String, nullable=True)
    response_payload = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "email": self.email,
            "provider": self.provider,
            "status": self.status,
            "external_reference": self.external_reference,
            "response_payload": self.response_payload or {},
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HostedEmailSendLog(Base):
    __tablename__ = "hosted_email_send_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(String, ForeignKey("user_email_accounts.id"), nullable=False, index=True)
    sender_email = Column(String, nullable=False, index=True)
    sender_domain = Column(String, nullable=False, index=True)
    recipient_email = Column(String, nullable=False, index=True)
    recipient_domain = Column(String, nullable=False, index=True)
    subject_hash = Column(String, nullable=True)
    body_hash = Column(String, nullable=True)
    link_count = Column(Integer, default=0)
    spam_score = Column(Float, default=0.0)
    blocked = Column(Boolean, default=False, index=True)
    block_reason = Column(String, nullable=True)
    ai_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_hosted_send_user_day", "user_id", "created_at"),
        Index("idx_hosted_send_domain_day", "sender_domain", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "sender_email": self.sender_email,
            "sender_domain": self.sender_domain,
            "recipient_email": self.recipient_email,
            "recipient_domain": self.recipient_domain,
            "spam_score": self.spam_score,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "ai_flagged": self.ai_flagged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

