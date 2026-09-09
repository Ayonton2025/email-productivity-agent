"""Billing addons definitions."""

import uuid
from datetime import datetime

from sqlalchemy import DECIMAL, JSON, Boolean, Column, DateTime, ForeignKey, Integer, String

from app.models.base import Base


class OutboundAddOn(Base):
    """
    Cold email & outbound is a separate revenue engine.
    Users can add campaign packages on top of base subscription.
    """

    __tablename__ = "outbound_addons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Which package?
    package_id = Column(String, nullable=False)  # starter, growth, scale
    package_name = Column(String, nullable=False)

    # Pricing
    price_usd = Column(DECIMAL(10, 2), nullable=False)
    billing_cycle = Column(String, default="monthly")

    # Volume limits
    sends_monthly_allocation = Column(Integer, nullable=False)
    sends_monthly_used = Column(Integer, default=0)

    # Dates
    started_at = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime, default=datetime.utcnow)
    period_end = Column(DateTime, nullable=False)

    # Status
    status = Column(String, default="active")  # active, paused, cancelled
    auto_renew = Column(Boolean, default=True)

    # Features included with this package
    features = Column(JSON, default={})

    # Addon Metadata
    addon_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EnterpriseAddOn(Base):
    """
    Enterprise customers can purchase specialized modules.
    These are high-value, high-margin add-ons.
    """

    __tablename__ = "enterprise_addons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Module type
    module_id = Column(String, nullable=False, index=True)  # governance, private_models, etc
    module_name = Column(String, nullable=False)

    # Pricing
    price_usd = Column(DECIMAL(10, 2), nullable=False)
    billing_cycle = Column(String, default="annual")  # usually annual
    billing_type = Column(String, default="per_module")  # per_module, per_seat, per_agent, custom

    # Quantity (if applicable)
    quantity = Column(Integer, default=1)  # For per-seat or per-agent modules

    # Dates
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=True)

    # Status
    status = Column(String, default="active")  # active, suspended, cancelled

    # Module Configuration
    config = Column(JSON, default={})  # Module-specific config
    module_metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
