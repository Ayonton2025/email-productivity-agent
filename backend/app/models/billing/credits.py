"""Billing credits definitions."""

import uuid
from datetime import datetime

from sqlalchemy import DECIMAL, Column, DateTime, ForeignKey, Integer, String, Text

from app.models.database import Base


class AICredits(Base):
    """
    Per-user AI credits balance and breakdown by action type.
    """

    __tablename__ = "ai_credits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Balances
    balance = Column(Integer, default=0)  # Available credits
    monthly_allocation = Column(Integer, default=0)
    monthly_used = Column(Integer, default=0)

    # Per-action counters
    classification_used = Column(Integer, default=0)
    extraction_used = Column(Integer, default=0)
    summarization_used = Column(Integer, default=0)
    sentiment_analysis_used = Column(Integer, default=0)
    other_used = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "balance": self.balance,
            "monthly_allocation": self.monthly_allocation,
            "monthly_used": self.monthly_used,
            "classification_used": self.classification_used,
            "extraction_used": self.extraction_used,
            "summarization_used": self.summarization_used,
            "sentiment_analysis_used": self.sentiment_analysis_used,
            "other_used": self.other_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class OutboundCredits(Base):
    """
    Per-user outbound email credits account.
    """

    __tablename__ = "outbound_credits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    balance = Column(Integer, default=0)
    monthly_allocation = Column(Integer, default=0)
    monthly_used = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "balance": self.balance,
            "monthly_allocation": self.monthly_allocation,
            "monthly_used": self.monthly_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AccountCredit(Base):
    """
    Manual credits given for promotions, refunds, or testing.
    """

    __tablename__ = "account_credits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Credit info
    credit_type = Column(String, nullable=False)  # promotion, refund, testing, gift
    amount_usd = Column(DECIMAL(10, 2), nullable=False)
    amount_ai_units = Column(Integer, default=0)  # Alternative: AI units instead of USD
    amount_email_sends = Column(Integer, default=0)

    # Validity
    expires_at = Column(DateTime, nullable=True)  # None = never expires
    used_at = Column(DateTime, nullable=True)

    # Reason
    reason = Column(Text, nullable=True)
    issued_by = Column(String, nullable=True)  # Admin user_id

    # Status
    status = Column(String, default="active")  # active, used, expired, cancelled

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


CREDIT_PACK_PRICING_USD = {
    1000: 4.0,
    5000: 15.0,
    10000: 25.0,
}
