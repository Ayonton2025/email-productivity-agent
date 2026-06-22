"""
Layer 7: Monetization Service

Implements complete hybrid monetization:
- Subscriptions (base layer)
- AI usage credits (per-action metering)
- Outbound volume (email sends)
- Enterprise modules (add-ons)
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.billing_models import (
    Subscription, PaymentTransaction, UsageLog, MonthlyBillingSnapshot,
    AIUsageUnit, OutboundAddOn, EnterpriseAddOn, AccountCredit,
    SUBSCRIPTION_PLANS, OUTBOUND_PACKAGES, ENTERPRISE_MODULES, AI_ACTION_COSTS, OVERAGE_PRICING
)


class SubscriptionService:
    """Manage user subscriptions and tier transitions"""
    
    @staticmethod
    async def create_subscription(user_id: str, tenant_id: str, plan_id: str, session: AsyncSession):
        """Create new subscription for user"""
        if plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {plan_id}")
        
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        current_period_end = datetime.utcnow() + timedelta(days=30)
        
        subscription = Subscription(
            user_id=user_id,
            tenant_id=tenant_id,
            plan_id=plan_id,
            plan_name=plan["name"],
            price_usd=Decimal(str(plan["price"])),
            price_per_seat=Decimal(str(plan.get("price_per_seat", 0))),
            seats_max=plan.get("seats", 1) or 999,
            ai_credits_monthly_allocation=plan["ai_credits_monthly"] or 0,
            outbound_emails_monthly_allocation=plan["outbound_emails_monthly"] or 0,
            features=plan.get("features", {}),
            current_period_end=current_period_end,
            ai_credits_reset_date=current_period_end
        )
        
        session.add(subscription)
        await session.flush()
        return subscription
    
    @staticmethod
    async def upgrade_subscription(user_id: str, new_plan_id: str, session: AsyncSession):
        """Upgrade user to higher tier"""
        if new_plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {new_plan_id}")
        
        query = select(Subscription).where(Subscription.user_id == user_id)
        result = await session.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"No subscription for user {user_id}")
        
        new_plan = SUBSCRIPTION_PLANS[new_plan_id]
        
        # Reset usage when upgrading
        subscription.plan_id = new_plan_id
        subscription.plan_name = new_plan["name"]
        subscription.price_usd = Decimal(str(new_plan["price"]))
        subscription.ai_credits_monthly_used = 0
        subscription.outbound_emails_monthly_used = 0
        subscription.features = new_plan.get("features", {})
        
        await session.flush()
        return subscription
    
    @staticmethod
    async def get_subscription(user_id: str, session: AsyncSession) -> Optional[Subscription]:
        """Retrieve user's subscription"""
        query = select(Subscription).where(Subscription.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


class AICreditService:
    """
    Manage AI credits - per-action metering system.
    
    Every AI operation costs a certain number of units.
    Users pay via subscription tiers + overages.
    """
    
    @staticmethod
    async def check_credits_available(
        user_id: str,
        action: str,
        session: AsyncSession
    ) -> bool:
        """Check if user has enough credits for action"""
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return False
        
        # Get action cost
        if action not in AI_ACTION_COSTS:
            raise ValueError(f"Unknown AI action: {action}")
        
        cost = AI_ACTION_COSTS[action]["units"]
        
        # Check monthly allocation
        available = subscription.ai_credits_monthly_allocation - subscription.ai_credits_monthly_used
        
        return available >= cost
    
    @staticmethod
    async def deduct_credits(
        user_id: str,
        action: str,
        model: str,
        session: AsyncSession,
        metadata: Dict = None
    ) -> Dict:
        """
        Deduct credits for AI action.
        
        Returns:
            {
                "success": bool,
                "units_consumed": int,
                "cost_usd": float,
                "remaining": int,
                "message": str
            }
        """
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return {
                "success": False,
                "message": "No subscription found"
            }
        
        if action not in AI_ACTION_COSTS:
            return {
                "success": False,
                "message": f"Unknown AI action: {action}"
            }
        
        cost = AI_ACTION_COSTS[action]["units"]
        available = subscription.ai_credits_monthly_allocation - subscription.ai_credits_monthly_used
        
        # Check if enough credits
        if available < cost:
            return {
                "success": False,
                "message": f"Insufficient credits. Need {cost}, have {available}",
                "remaining": available
            }
        
        # Deduct credits
        subscription.ai_credits_monthly_used += cost
        
        # Log usage
        usage = AIUsageUnit(
            user_id=user_id,
            tenant_id=subscription.tenant_id,
            feature=action,
            action=action,
            units_consumed=cost,
            units_actual=cost,
            usd_cost=Decimal(str(cost * 0.001)),  # $1 per 1000 units
            model=model,
            metadata=metadata or {}
        )
        session.add(usage)
        
        # Log in usage_logs for analytics
        usage_log = UsageLog(
            user_id=user_id,
            tenant_id=subscription.tenant_id,
            metric=f"ai_{action}_used",
            quantity=cost
        )
        session.add(usage_log)
        
        await session.flush()
        
        return {
            "success": True,
            "units_consumed": cost,
            "cost_usd": float(cost * 0.001),
            "remaining": subscription.ai_credits_monthly_allocation - subscription.ai_credits_monthly_used,
            "message": "Credits deducted successfully"
        }
    
    @staticmethod
    async def get_credits_balance(user_id: str, session: AsyncSession) -> Dict:
        """Get current credit balance and stats"""
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return {
                "balance": 0,
                "allocated": 0,
                "used": 0,
                "available": 0
            }
        
        return {
            "balance": subscription.ai_credits_monthly_allocation,
            "allocated": subscription.ai_credits_monthly_allocation,
            "used": subscription.ai_credits_monthly_used,
            "available": subscription.ai_credits_monthly_allocation - subscription.ai_credits_monthly_used,
            "reset_date": subscription.ai_credits_reset_date.isoformat() if subscription.ai_credits_reset_date else None
        }


class OutboundEmailService:
    """
    Manage outbound email volume limits.
    
    Base subscription includes some sends.
    Users can add extra packages or track volume.
    """
    
    @staticmethod
    async def check_outbound_available(
        user_id: str,
        count: int,
        session: AsyncSession
    ) -> bool:
        """Check if user can send N emails"""
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return False
        
        available = subscription.outbound_emails_monthly_allocation - subscription.outbound_emails_monthly_used
        return available >= count
    
    @staticmethod
    async def deduct_outbound(
        user_id: str,
        count: int,
        session: AsyncSession,
        campaign_type: str = "general"
    ) -> Dict:
        """
        Deduct outbound email limit.
        
        Returns:
            {"success": bool, "remaining": int}
        """
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return {"success": False, "message": "No subscription"}
        
        available = subscription.outbound_emails_monthly_allocation - subscription.outbound_emails_monthly_used
        
        if available < count:
            return {
                "success": False,
                "message": f"Insufficient outbound quota. Need {count}, have {available}",
                "remaining": available
            }
        
        subscription.outbound_emails_monthly_used += count
        
        # Log
        usage_log = UsageLog(
            user_id=user_id,
            tenant_id=subscription.tenant_id,
            metric="outbound_emails_sent",
            quantity=count,
            breakdown={"campaign_type": campaign_type}
        )
        session.add(usage_log)
        
        await session.flush()
        
        return {
            "success": True,
            "sent": count,
            "remaining": subscription.outbound_emails_monthly_allocation - subscription.outbound_emails_monthly_used
        }
    
    @staticmethod
    async def add_outbound_addon(
        user_id: str,
        tenant_id: str,
        package_id: str,
        session: AsyncSession
    ):
        """Add outbound campaign package"""
        if package_id not in OUTBOUND_PACKAGES:
            raise ValueError(f"Unknown package: {package_id}")
        
        package = OUTBOUND_PACKAGES[package_id]
        
        addon = OutboundAddOn(
            user_id=user_id,
            tenant_id=tenant_id,
            package_id=package_id,
            package_name=package["name"],
            price_usd=Decimal(str(package["price"])),
            sends_monthly_allocation=package["sends_monthly"],
            features=package.get("features", {}),
            period_end=datetime.utcnow() + timedelta(days=30)
        )
        
        session.add(addon)
        await session.flush()
        return addon


class FeatureGatingService:
    """
    Control feature access based on subscription tier and credits.
    
    Every feature requires specific tier + enough credits.
    """
    
    @staticmethod
    async def can_access_feature(
        user_id: str,
        feature: str,
        session: AsyncSession
    ) -> Dict:
        """
        Check if user can access feature.
        
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "required_tier": str,
                "current_tier": str
            }
        """
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return {
                "allowed": False,
                "reason": "No subscription",
                "current_tier": None
            }
        
        # Check if feature is in subscription's features
        features = subscription.features or {}
        
        if feature not in features or not features[feature]:
            return {
                "allowed": False,
                "reason": f"Feature not included in {subscription.plan_name} tier",
                "required_tier": "Higher",
                "current_tier": subscription.plan_id
            }
        
        return {
            "allowed": True,
            "reason": "Feature access granted",
            "current_tier": subscription.plan_id
        }
    
    @staticmethod
    async def check_team_limit(
        user_id: str,
        session: AsyncSession
    ) -> Dict:
        """Check team member limit"""
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return {"allowed": False, "reason": "No subscription"}
        
        if subscription.seats_current >= subscription.seats_max:
            return {
                "allowed": False,
                "reason": f"Team limit reached ({subscription.seats_max} seats)",
                "current": subscription.seats_current,
                "max": subscription.seats_max
            }
        
        return {
            "allowed": True,
            "current": subscription.seats_current,
            "max": subscription.seats_max,
            "available": subscription.seats_max - subscription.seats_current
        }


class EnterpriseBillingService:
    """Enterprise-specific billing features"""
    
    @staticmethod
    async def add_enterprise_module(
        user_id: str,
        tenant_id: str,
        module_id: str,
        session: AsyncSession
    ):
        """Add enterprise module"""
        if module_id not in ENTERPRISE_MODULES:
            raise ValueError(f"Unknown module: {module_id}")
        
        module = ENTERPRISE_MODULES[module_id]
        
        addon = EnterpriseAddOn(
            user_id=user_id,
            tenant_id=tenant_id,
            module_id=module_id,
            module_name=module["name"],
            price_usd=Decimal(str(module["price"])),
            billing_cycle=module.get("billing_cycle", "annual"),
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        
        session.add(addon)
        await session.flush()
        return addon
    
    @staticmethod
    async def get_enterprise_modules(
        user_id: str,
        session: AsyncSession
    ) -> List[Dict]:
        """Get active enterprise modules for user"""
        query = select(EnterpriseAddOn).where(
            (EnterpriseAddOn.user_id == user_id) &
            (EnterpriseAddOn.status == "active")
        )
        result = await session.execute(query)
        addons = result.scalars().all()
        
        return [
            {
                "module_id": addon.module_id,
                "module_name": addon.module_name,
                "price": float(addon.price_usd),
                "billing_cycle": addon.billing_cycle,
                "expires_at": addon.expires_at.isoformat()
            }
            for addon in addons
        ]


class BillingReportService:
    """Generate billing reports and analytics"""
    
    @staticmethod
    async def generate_monthly_snapshot(
        user_id: str,
        session: AsyncSession
    ):
        """Generate monthly billing snapshot"""
        subscription = await SubscriptionService.get_subscription(user_id, session)
        if not subscription:
            return None
        
        now = datetime.utcnow()
        
        # Calculate costs
        subscription_cost = subscription.price_usd
        
        # Get add-ons
        addon_query = select(OutboundAddOn).where(
            (OutboundAddOn.user_id == user_id) &
            (OutboundAddOn.status == "active")
        )
        addon_result = await session.execute(addon_query)
        addons = addon_result.scalars().all()
        addon_cost = sum(Decimal(str(a.price_usd)) for a in addons)
        
        # Calculate overage
        overages_used = subscription.ai_credits_monthly_used - subscription.ai_credits_monthly_allocation
        overage_cost = Decimal(0)
        if overages_used > 0:
            overage_cost = Decimal(str(overages_used)) * Decimal(str(OVERAGE_PRICING["per_1000_units"])) / Decimal("1000")
        
        total_cost = subscription_cost + addon_cost + overage_cost
        
        snapshot = MonthlyBillingSnapshot(
            user_id=user_id,
            tenant_id=subscription.tenant_id,
            year=now.year,
            month=now.month,
            ai_credits_allocated=subscription.ai_credits_monthly_allocation,
            ai_credits_used=subscription.ai_credits_monthly_used,
            ai_credits_overages=max(0, overages_used),
            outbound_emails_allocated=subscription.outbound_emails_monthly_allocation,
            outbound_emails_sent=subscription.outbound_emails_monthly_used,
            subscription_cost=subscription_cost,
            addon_cost=addon_cost,
            overage_cost=overage_cost,
            total_cost=total_cost
        )
        
        session.add(snapshot)
        await session.flush()
        return snapshot
