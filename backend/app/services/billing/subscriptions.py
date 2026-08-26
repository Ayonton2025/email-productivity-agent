import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import SubscriptionError
from app.core.security import logger
from app.models.billing_models import (
    AI_ACTION_COSTS,
    CREDIT_PACK_PRICING_USD,
    SUBSCRIPTION_PLANS,
    AICredits,
    CreditTransaction,
    OutboundCredits,
    Payment,
    PaymentTransaction,
    Subscription,
    UsageLog,
)
from app.models.database import SystemSetting, User
from app.services.billing.paystack import PaystackService


class SubscriptionService:
    """Manage user subscriptions"""

    def __init__(self):
        self.paystack = PaystackService()

    async def create_subscription(
        self, user_id: str, tenant_id: str, plan_id: str, session: AsyncSession
    ) -> Subscription:
        """Create a new subscription"""

        if plan_id not in SUBSCRIPTION_PLANS:
            raise SubscriptionError(f"Unknown plan: {plan_id}")

        plan = SUBSCRIPTION_PLANS[plan_id]

        cycle = plan.get("billing_cycle", "monthly")
        if cycle == "daily":
            period_days = 1
        elif cycle == "annual":
            period_days = 365
        else:
            period_days = 30
        seats_value = plan.get("seats")
        seats_value = seats_value if seats_value is not None else 999
        credits_allocation = plan.get("ai_credits_daily") or plan.get("ai_credits_monthly") or 0
        period_start = datetime.utcnow()
        period_end = period_start + timedelta(days=period_days)

        subscription = Subscription(
            user_id=user_id,
            tenant_id=tenant_id,
            plan_id=plan_id,
            plan_name=plan["name"],
            billing_cycle=plan.get("billing_cycle", "monthly"),
            price_usd=plan.get("price", 0),
            price_per_seat=plan.get("price_per_seat", 0),
            current_period_start=period_start,
            current_period_end=period_end,
            billing_cycle_start=period_start,
            billing_cycle_end=period_end,
            seats_included=seats_value,
            seats_current=min(1, seats_value),
            seats_max=seats_value,
            features=plan.get("features", {}),
            ai_credits_monthly_allocation=credits_allocation,
            outbound_emails_monthly_allocation=plan.get("outbound_emails_monthly") or 0,
            ai_credits_reset_date=period_end,
            credits_total=credits_allocation,
            credits_used=0,
        )

        session.add(subscription)
        await session.flush()

        # Initialize AI and Outbound credits
        ai_credits = AICredits(
            user_id=user_id, tenant_id=tenant_id, balance=credits_allocation, monthly_allocation=credits_allocation
        )

        outbound_credits = OutboundCredits(
            user_id=user_id,
            tenant_id=tenant_id,
            balance=plan.get("outbound_emails_monthly") or 0,
            monthly_allocation=plan.get("outbound_emails_monthly") or 0,
        )

        session.add(ai_credits)
        session.add(outbound_credits)
        session.add(
            CreditTransaction(
                user_id=user_id,
                credits_added=credits_allocation,
                source="subscription",
            )
        )

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = plan_id
            user.subscription_status = "active" if plan.get("price", 0) > 0 else "free"

        return subscription

    async def upgrade_subscription(self, user_id: str, new_plan_id: str, session: AsyncSession) -> Subscription:
        """Upgrade a subscription to a different plan"""

        result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        subscription = result.scalar()

        if not subscription:
            raise SubscriptionError(f"No subscription found for user {user_id}")

        plan = SUBSCRIPTION_PLANS[new_plan_id]

        # Update subscription
        seats_value = plan.get("seats")
        seats_value = seats_value if seats_value is not None else 999

        subscription.plan_id = new_plan_id
        subscription.plan_name = plan["name"]
        subscription.price_usd = plan.get("price", 0)
        subscription.price_per_seat = plan.get("price_per_seat", 0)
        subscription.seats_included = seats_value
        subscription.seats_max = seats_value
        subscription.features = plan.get("features", {})
        credits_allocation = plan.get("ai_credits_daily") or plan.get("ai_credits_monthly") or 0
        subscription.ai_credits_monthly_allocation = credits_allocation
        subscription.outbound_emails_monthly_allocation = plan.get("outbound_emails_monthly") or 0
        subscription.credits_total = credits_allocation
        subscription.credits_used = 0
        subscription.billing_cycle_start = datetime.utcnow()
        if plan.get("billing_cycle") == "daily":
            subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=1)
        elif plan.get("billing_cycle") == "annual":
            subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=365)
        else:
            subscription.billing_cycle_end = datetime.utcnow() + timedelta(days=30)
        subscription.current_period_start = subscription.billing_cycle_start
        subscription.current_period_end = subscription.billing_cycle_end
        subscription.updated_at = datetime.utcnow()

        # Reset monthly usage
        subscription.ai_credits_monthly_used = 0
        subscription.outbound_emails_monthly_used = 0

        ai_result = await session.execute(select(AICredits).where(AICredits.user_id == user_id))
        ai_credits = ai_result.scalar_one_or_none()
        if ai_credits:
            ai_credits.monthly_allocation = credits_allocation
            ai_credits.balance = credits_allocation
            ai_credits.monthly_used = 0

        session.add(
            CreditTransaction(
                user_id=user_id,
                credits_added=credits_allocation,
                source="subscription",
            )
        )

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = new_plan_id
            user.subscription_status = "active" if plan.get("price", 0) > 0 else "free"

        await session.flush()
        return subscription

    async def cancel_subscription(self, user_id: str, session: AsyncSession) -> Subscription:
        """Cancel a subscription"""

        result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        subscription = result.scalar()

        if not subscription:
            raise SubscriptionError(f"No subscription found for user {user_id}")

        subscription.status = "cancelled"
        subscription.auto_renew = False
        subscription.updated_at = datetime.utcnow()
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = "personal"
            user.subscription_status = "cancelled"

        await session.flush()
        return subscription

    async def get_subscription(self, user_id: str, session: AsyncSession) -> Optional[Subscription]:
        """Get user's subscription"""
        result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        return result.scalar()

    async def renew_subscription(self, user_id: str, session: AsyncSession) -> Subscription:
        """Reactivate a subscription and advance its billing period."""
        result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        subscription = result.scalar()
        if not subscription:
            raise SubscriptionError(f"No subscription found for user {user_id}")

        cycle_days = {"daily": 1, "annual": 365}.get(subscription.billing_cycle, 30)
        period_start = datetime.utcnow()
        period_end = period_start + timedelta(days=cycle_days)
        subscription.status = "active"
        subscription.auto_renew = True
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.billing_cycle_start = period_start
        subscription.billing_cycle_end = period_end
        subscription.renewal_date = period_end
        subscription.updated_at = period_start

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.plan = subscription.plan_id
            user.subscription_status = "active"

        await session.flush()
        return subscription
