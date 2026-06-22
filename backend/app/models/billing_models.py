"""
Layer 7: Monetization & Billing Models

Hybrid monetization:
- Base subscription (seats)
- AI usage (credits per action)
- Outbound volume (email sends)
- Enterprise modules (add-ons)
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey, Index, Float, DECIMAL
from datetime import datetime
import uuid
import json

from app.models.database import Base


# ============================================================================
# SUBSCRIPTION TIERS - Base Product Layer
# ============================================================================

class Subscription(Base):
    """
    User's current subscription tier.
    Defines access level, included credits, and team limits.
    """
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, unique=True, index=True)
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
    seats_max = Column(Integer, default=1)      # Hard limit
    
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
        Index('idx_subscription_status', 'status'),
        Index('idx_subscription_renewal', 'renewal_date'),
    )


# ============================================================================
# SUBSCRIPTION PLANS - Configuration
# ============================================================================

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
        "description": "1 email account, 50 AI credits/day, basic prioritization and replies"
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
        "description": "3 email accounts, 1,500 AI credits/month, smart replies, workflow triggers, dashboard"
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
        "description": "Unlimited accounts, 5,000 AI credits/month, advanced workflows, analytics, API access"
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
        "description": "Enterprise plan - custom pricing and features based on requirements"
    }
}


# ============================================================================
# AI USAGE BILLING - Per-Action Cost System
# ============================================================================

class AIUsageUnit(Base):
    """
    Every AI operation costs credits.
    This allows us to meter AI compute and prevent abuse.
    """
    __tablename__ = "ai_usage_units"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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


# AI Action costs - Non-negotiable pricing
AI_ACTION_COSTS = {
    "categorization": {
        "units": 1,
        "description": "Workflow classification"
    },
    "summarization": {
        "units": 1,
        "description": "Email summary"
    },
    "action_extraction": {
        "units": 1,
        "description": "Workflow classification"
    },
    "sentiment_analysis": {
        "units": 1,
        "description": "Analyze sentiment and tone"
    },
    "reply_drafting": {
        "units": 2,
        "description": "Generate suggested reply"
    },
    "workflow_agent_run": {
        "units": 5,
        "description": "Execute workflow rule/agent"
    },
    "outbound_personalization": {
        "units": 3,
        "description": "Personalize outbound email"
    },
    "risk_analysis": {
        "units": 2,
        "description": "Detect risks and issues"
    },
    "relationship_scoring": {
        "units": 2,
        "description": "Score relationship quality"
    },
    "legal_analysis": {
        "units": 5,
        "description": "Analyze contracts and legal risks"
    },
    "security_scan": {
        "units": 2,
        "description": "Phishing and scam analysis"
    },
    "meeting_intelligence": {
        "units": 2,
        "description": "Meeting detection, slots, and prep"
    },
    "commitment_detection": {
        "units": 2,
        "description": "Detect promises and commitments"
    },
}

CREDIT_PACK_PRICING_USD = {
    1000: 4.0,
    5000: 15.0,
    10000: 25.0,
}

# Overage pricing
OVERAGE_PRICING = {
    "base_price": 10,  # Base price per 1000 units
    "per_1000_units": 10,  # $10 per 1000 overage units
    "max_daily_overage": None,  # None = unlimited
}


# ============================================================================
# AI & OUTBOUND CREDIT ACCOUNTS
# ============================================================================

class AICredits(Base):
    """
    Per-user AI credits balance and breakdown by action type.
    """
    __tablename__ = "ai_credits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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


# ============================================================================
# OUTBOUND EMAIL VOLUME - Separate Add-On System
# ============================================================================

class OutboundAddOn(Base):
    """
    Cold email & outbound is a separate revenue engine.
    Users can add campaign packages on top of base subscription.
    """
    __tablename__ = "outbound_addons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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


# Outbound add-on packages
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
        "description": "Perfect for getting started with cold email"
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
        "description": "Scale your campaigns with advanced features"
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
        "description": "Enterprise-grade campaign management"
    }
}


# ============================================================================
# ENTERPRISE ADD-ON MODULES
# ============================================================================

class EnterpriseAddOn(Base):
    """
    Enterprise customers can purchase specialized modules.
    These are high-value, high-margin add-ons.
    """
    __tablename__ = "enterprise_addons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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


# Enterprise modules with exact pricing
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
    },
}


# ============================================================================
# PAYMENT TRANSACTIONS
# ============================================================================

class PaymentTransaction(Base):
    """
    Record every payment attempt and completion.
    Covers subscription renewals, add-on purchases, and overage charges.
    """
    __tablename__ = "payment_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # paystack/paypal
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="pending", index=True)
    reference = Column(String, nullable=True, index=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    credits_added = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    source = Column(String, nullable=False, index=True)  # free/subscription/purchase/usage
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# ============================================================================
# USAGE TRACKING & ANALYTICS
# ============================================================================

class UsageLog(Base):
    """
    Track all usage for billing and analytics.
    Monthly aggregation for reports.
    """
    __tablename__ = "usage_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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
        Index('idx_user_metric_date', 'user_id', 'metric', 'created_at'),
        Index('idx_tenant_metric_date', 'tenant_id', 'metric', 'created_at'),
    )


class MonthlyBillingSnapshot(Base):
    """
    Pre-calculated monthly billing data for fast reporting.
    Created on each 1st of month.
    """
    __tablename__ = "monthly_billing_snapshots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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
        Index('idx_user_year_month', 'user_id', 'year', 'month', unique=True),
        Index('idx_tenant_year_month', 'tenant_id', 'year', 'month'),
    )


class AccountCredit(Base):
    """
    Manual credits given for promotions, refunds, or testing.
    """
    __tablename__ = "account_credits"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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
