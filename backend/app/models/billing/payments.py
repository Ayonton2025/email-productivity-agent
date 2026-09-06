"""Billing payments definitions."""

import uuid
from datetime import datetime

from sqlalchemy import DECIMAL, JSON, Column, DateTime, ForeignKey, Integer, String, Text

from app.models.database import Base


class PaymentTransaction(Base):
    """
    Record every payment attempt and completion.
    Covers subscription renewals, add-on purchases, and overage charges.
    """

    __tablename__ = "payment_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # What are we charging for?
    charge_type = Column(String, nullable=False)  # subscription, addon, overage, manual
    reference_id = Column(String, nullable=True)  # subscription_id, addon_id, etc

    # Amount
    amount_usd = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String, default="USD")

    # Payment method
    payment_method = Column(String, nullable=False)  # paystack, stripe, bank_transfer
    payment_reference = Column(String, nullable=True)  # External payment ID

    # Status
    status = Column(String, default="pending")  # pending, completed, failed, refunded
    failure_reason = Column(Text, nullable=True)

    # Dates
    attempted_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    # Payment Metadata
    payment_metadata = Column(JSON, default={})  # Invoice number, receipt, etc

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # paystack/paypal
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="pending", index=True)
    reference = Column(String, nullable=True, index=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    credits_added = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    source = Column(String, nullable=False, index=True)  # free/subscription/purchase/usage
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
