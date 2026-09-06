"""Billing usage definitions."""

import uuid
from datetime import datetime

from sqlalchemy import DECIMAL, JSON, Column, DateTime, ForeignKey, Index, Integer, String

from app.models.database import Base


class AIUsageUnit(Base):
    """
    Every AI operation costs credits.
    This allows us to meter AI compute and prevent abuse.
    """

    __tablename__ = "ai_usage_units"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # What action cost credits?
    feature = Column(String, nullable=False, index=True)  # 'categorization', 'summarization', etc
    action = Column(String, nullable=False)  # More specific action name

    # How many credits?
    units_consumed = Column(Integer, nullable=False)  # Base cost
    units_actual = Column(Integer, nullable=False)  # With modifiers (premium model, etc)

    # Cost in USD (for analytics)
    usd_cost = Column(DECIMAL(10, 4), nullable=False)

    # Model used
    model = Column(String, nullable=False)  # gpt-4, gpt-3.5-turbo, claude-3, etc

    # Usage Metadata
    usage_metadata = Column(JSON, default={})  # tokens, response_quality, etc

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


AI_ACTION_COSTS = {
    "categorization": {"units": 1, "description": "Workflow classification"},
    "summarization": {"units": 1, "description": "Email summary"},
    "action_extraction": {"units": 1, "description": "Workflow classification"},
    "sentiment_analysis": {"units": 1, "description": "Analyze sentiment and tone"},
    "reply_drafting": {"units": 2, "description": "Generate suggested reply"},
    "workflow_agent_run": {"units": 5, "description": "Execute workflow rule/agent"},
    "outbound_personalization": {"units": 3, "description": "Personalize outbound email"},
    "risk_analysis": {"units": 2, "description": "Detect risks and issues"},
    "relationship_scoring": {"units": 2, "description": "Score relationship quality"},
    "legal_analysis": {"units": 5, "description": "Analyze contracts and legal risks"},
    "security_scan": {"units": 2, "description": "Phishing and scam analysis"},
    "meeting_intelligence": {"units": 2, "description": "Meeting detection, slots, and prep"},
    "commitment_detection": {"units": 2, "description": "Detect promises and commitments"},
}

OVERAGE_PRICING = {
    "base_price": 10,  # Base price per 1000 units
    "per_1000_units": 10,  # $10 per 1000 overage units
    "max_daily_overage": None,  # None = unlimited
}


class UsageLog(Base):
    """
    Track all usage for billing and analytics.
    Monthly aggregation for reports.
    """

    __tablename__ = "usage_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # What happened?
    metric = Column(String, nullable=False, index=True)  # ai_credits_used, emails_sent, etc
    quantity = Column(Integer, nullable=False)
    action = Column(String, nullable=True, index=True)
    tokens_used = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Breakdown
    breakdown = Column(JSON, default={})  # Detailed breakdown if applicable

    # Created
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_user_metric_date", "user_id", "metric", "created_at"),
        Index("idx_tenant_metric_date", "tenant_id", "metric", "created_at"),
    )


class MonthlyBillingSnapshot(Base):
    """
    Pre-calculated monthly billing data for fast reporting.
    Created on each 1st of month.
    """

    __tablename__ = "monthly_billing_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Which month?
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    # Usage data
    ai_credits_allocated = Column(Integer, default=0)
    ai_credits_used = Column(Integer, default=0)
    ai_credits_overages = Column(Integer, default=0)

    outbound_emails_allocated = Column(Integer, default=0)
    outbound_emails_sent = Column(Integer, default=0)
    outbound_emails_overages = Column(Integer, default=0)

    # Costs
    subscription_cost = Column(DECIMAL(10, 2), default=0)
    addon_cost = Column(DECIMAL(10, 2), default=0)
    overage_cost = Column(DECIMAL(10, 2), default=0)
    total_cost = Column(DECIMAL(10, 2), default=0)

    # Billing Metadata
    billing_metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_year_month", "user_id", "year", "month", unique=True),
        Index("idx_tenant_year_month", "tenant_id", "year", "month"),
    )


OUTBOUND_PACKAGES = {
    "starter": {
        "name": "Starter Campaign Pack",
        "price": 19,
        "sends_monthly": 2000,
        "features": {
            "personalization_engine": True,
            "reply_detection": True,
            "ab_testing": False,
            "warm_up_system": False,
            "sentiment_scoring": False,
            "webhooks": False,
            "deliverability_tools": False,
            "enrichment": False,
            "revenue_analytics": False,
        },
        "description": "Perfect for getting started with cold email",
    },
    "growth": {
        "name": "Growth Campaign Pack",
        "price": 49,
        "sends_monthly": 10000,
        "features": {
            "personalization_engine": True,
            "reply_detection": True,
            "ab_testing": True,
            "warm_up_system": True,
            "sentiment_scoring": True,
            "webhooks": False,
            "deliverability_tools": False,
            "enrichment": False,
            "revenue_analytics": False,
        },
        "description": "Scale your campaigns with advanced features",
    },
    "scale": {
        "name": "Scale Campaign Pack",
        "price": 99,
        "sends_monthly": 100000,  # 50k-250k range, using 100k as average
        "features": {
            "personalization_engine": True,
            "reply_detection": True,
            "ab_testing": True,
            "warm_up_system": True,
            "sentiment_scoring": True,
            "webhooks": True,
            "deliverability_tools": True,
            "enrichment": True,
            "revenue_analytics": True,
            "dedicated_ip_pools": False,  # Enterprise only
            "compliance_filters": False,
        },
        "description": "Enterprise-grade campaign management",
    },
}

ENTERPRISE_MODULES = {
    "ai_governance": {
        "name": "AI Governance & Compliance Module",
        "price": 5000,
        "billing_cycle": "annual",
        "description": "Control AI behavior, policies, custom guardrails",
        "includes": [
            "Custom AI policy engine",
            "Model selection control",
            "Output validation rules",
            "Compliance checklist",
            "Risk detection",
        ],
    },
    "private_models": {
        "name": "Private Model Hosting",
        "price": 1000,
        "billing_cycle": "monthly",
        "description": "Run fine-tuned models on dedicated infrastructure",
        "includes": [
            "Dedicated compute",
            "Private model training",
            "Custom fine-tuning",
            "Performance optimization",
        ],
    },
    "audit_system": {
        "name": "Communication Audit System",
        "price": 10000,
        "billing_cycle": "annual",
        "description": "Full audit trails, compliance reporting, legal archiving",
        "includes": [
            "Full audit logs",
            "Compliance reporting",
            "Legal holds",
            "Data residency control",
            "Retention policies",
        ],
    },
    "custom_agents": {
        "name": "Custom Agent Development",
        "price": 3000,
        "billing_cycle": "one_time",
        "description": "Build organization-specific agents",
        "includes": [
            "Custom agent design",
            "Domain-specific training",
            "Integration setup",
            "Performance tuning",
        ],
    },
    "dedicated_infrastructure": {
        "name": "Dedicated Infrastructure",
        "price": 2000,
        "billing_cycle": "monthly",
        "description": "Private deployment, dedicated resources, premium SLA",
        "includes": [
            "Dedicated servers",
            "Private database",
            "Custom domain",
            "99.9% SLA",
            "Priority support",
        ],
    },
    "dedicated_ip_pools": {
        "name": "Dedicated IP Pools for Outbound",
        "price": 500,
        "billing_cycle": "monthly",
        "description": "Separate IP reputation, domain warming, compliance",
        "includes": [
            "Dedicated IPs",
            "Domain warming",
            "Blacklist monitoring",
            "Reputation management",
        ],
    },
}
