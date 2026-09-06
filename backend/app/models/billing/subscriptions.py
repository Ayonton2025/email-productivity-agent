"""Billing subscriptions definitions."""

import uuid
from datetime import datetime

from sqlalchemy import DECIMAL, JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String

from app.models.database import Base


class Subscription(Base):
    """
    User's current subscription tier.
    Defines access level, included credits, and team limits.
    """

    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # ---- Subscription Tier ----
    plan_id = Column(String, nullable=False, index=True)  # personal, plus, professional, team, enterprise
    plan_name = Column(String, nullable=False)

    # ---- Pricing ----
    billing_cycle = Column(String, default="monthly")  # monthly, annual
    price_usd = Column(DECIMAL(10, 2), nullable=False)
    price_per_seat = Column(DECIMAL(10, 2), default=0)  # For team/enterprise

    # ---- Dates ----
    started_at = Column(DateTime, default=datetime.utcnow)
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False)
    billing_cycle_start = Column(DateTime, default=datetime.utcnow)
    billing_cycle_end = Column(DateTime, nullable=True)

    # ---- Status ----
    status = Column(String, default="active")  # active, past_due, cancelled, suspended, trialing

    # ---- Renewal ----
    auto_renew = Column(Boolean, default=True)
    renewal_date = Column(DateTime, nullable=True)

    # ---- Payment ----
    payment_method = Column(String)  # stripe, paystack, bank_transfer
    payment_method_id = Column(String)
    payment_provider = Column(String, nullable=True)

    # ---- Team Seats ----
    seats_included = Column(Integer, default=1)  # How many users included
    seats_current = Column(Integer, default=1)  # Currently used
    seats_max = Column(Integer, default=1)  # Hard limit

    # ---- Feature Flags (by plan) ----
    features = Column(JSON, default={})  # {"workflows": True, "outbound_campaigns": False, ...}

    # ---- AI Credits (included monthly) ----
    ai_credits_monthly_allocation = Column(Integer, default=0)
    ai_credits_monthly_used = Column(Integer, default=0)
    credits_total = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    ai_credits_reset_date = Column(DateTime, nullable=True)

    # ---- Outbound Email Volume (if base tier includes it) ----
    outbound_emails_monthly_allocation = Column(Integer, default=0)
    outbound_emails_monthly_used = Column(Integer, default=0)

    # ---- Trial Info ----
    trial_ends_at = Column(DateTime, nullable=True)
    trial_cancelled_at = Column(DateTime, nullable=True)

    # ---- Plan Metadata ----
    plan_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_subscription_status", "status"),
        Index("idx_subscription_renewal", "renewal_date"),
    )


SUBSCRIPTION_PLANS = {
    "personal": {
        "name": "Free",
        "price": 0,
        "price_per_seat": 0,
        "billing_cycle": "daily",
        "email_accounts": 1,
        "seats": 1,
        "ai_credits_daily": 50,
        "ai_credits_monthly": 50,
        "outbound_emails_monthly": 0,
        "features": {
            "email_categorization": True,
            "email_summaries": True,
            "priority_inbox": True,
            "basic_auto_reply": True,
            "manual_ai_drafting": True,
            "workflows": False,
            "advanced_analytics": False,
            "api_access": False,
        },
        "description": "1 email account, 50 AI credits/day, basic prioritization and replies",
    },
    "plus": {
        "name": "Plus",
        "price": 12,
        "price_per_seat": 0,
        "billing_cycle": "monthly",
        "email_accounts": 3,
        "seats": 1,
        "ai_credits_monthly": 1500,
        "outbound_emails_monthly": 0,
        "features": {
            "email_categorization": True,
            "email_summaries": True,
            "priority_inbox": True,
            "advanced_auto_reply": True,
            "manual_ai_drafting": True,
            "workflows": True,
            "dashboard": True,
            "advanced_analytics": False,
            "api_access": False,
        },
        "description": "3 email accounts, 1,500 AI credits/month, smart replies, workflow triggers, dashboard",
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "price_per_seat": 0,
        "billing_cycle": "monthly",
        "email_accounts": None,
        "seats": 1,
        "ai_credits_monthly": 5000,
        "outbound_emails_monthly": 0,
        "features": {
            "email_categorization": True,
            "email_summaries": True,
            "priority_inbox": True,
            "advanced_auto_reply": True,
            "manual_ai_drafting": True,
            "workflows": True,
            "dashboard": True,
            "advanced_analytics": True,
            "api_access": True,
        },
        "description": "Unlimited accounts, 5,000 AI credits/month, advanced workflows, analytics, API access",
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 0,
        "price_per_seat": 0,
        "billing_cycle": "custom",
        "email_accounts": None,
        "seats": None,
        "ai_credits_monthly": None,
        "outbound_emails_monthly": None,
        "features": {
            "email_categorization": True,
            "email_summaries": True,
            "priority_inbox": True,
            "advanced_auto_reply": True,
            "manual_ai_drafting": True,
            "relationships_intelligence": True,
            "follow_up_assistant": True,
            "reminders_and_tracking": True,
            "tone_style_learning": True,
            "basic_insights_dashboard": True,
            "workflows": True,
            "smart_routing": True,
            "advanced_agents": True,
            "team_agents": True,
            "outbound_campaigns": True,
            "outbound_assistant": True,
            "auto_crm": True,
            "calendar_task_integration": True,
            "analytics_dashboard": True,
            "shared_inboxes": True,
            "workflow_builder": True,
            "approval_flows": True,
            "crm_lite": True,
            "integrations": True,
            "role_management": True,
            "basic_audit_logs": True,
            "advanced_analytics": True,
            "unlimited_workflows": True,
            "org_level_agents": True,
            "private_models": True,
            "custom_ai_policies": True,
            "compliance_tooling": True,
            "full_audit_trails": True,
            "data_residency": True,
            "sso": True,
            "sla_support": True,
            "dedicated_infrastructure": True,
            "api_access": True,
        },
        "description": "Enterprise plan - custom pricing and features based on requirements",
    },
}
