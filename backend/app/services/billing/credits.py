import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.billing_models import (
    AI_ACTION_COSTS,
    SUBSCRIPTION_PLANS,
    AICredits,
    CreditTransaction,
    OutboundCredits,
    Subscription,
    UsageLog,
)
from app.models.database import SystemSetting, User
from app.services.billing.paystack import PaymentRequiredError


class CreditService:
    """Manage AI and Outbound credits"""

    @staticmethod
    def _is_super_admin_email(email: Optional[str]) -> bool:
        allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
        return bool(email and email.lower() in allowed)

    @classmethod
    def _is_super_admin_user(cls, user: Optional[User]) -> bool:
        if not user:
            return False
        if getattr(user, "is_superuser", False) or getattr(user, "is_admin", False):
            return True
        if str(getattr(user, "plan", "")).strip().lower() == "super_admin":
            return True
        return cls._is_super_admin_email(getattr(user, "email", None))

    async def _get_user(self, user_id: str, session: AsyncSession) -> Optional[User]:
        row = await session.execute(select(User).where(User.id == user_id))
        return row.scalar_one_or_none()

    async def _get_user_access_override(
        self, user_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        user = await self._get_user(user_id, session)
        if not user or not user.email:
            return {}
        key = "user_access_overrides_v1"
        setting = await session.get(SystemSetting, key)
        if not setting or not setting.value:
            return {}
        try:
            payload = json.loads(setting.value)
            return (payload or {}).get(user.email.lower(), {}) or {}
        except Exception:
            return {}

    async def _has_payment_bypass(self, user_id: str, session: AsyncSession) -> bool:
        user = await self._get_user(user_id, session)
        if self._is_super_admin_user(user):
            return True
        override = await self._get_user_access_override(user_id, session)
        return bool(override.get("payment_bypass") or override.get("allow_all"))

    async def _is_user_blocked(self, user_id: str, session: AsyncSession) -> bool:
        override = await self._get_user_access_override(user_id, session)
        return bool(override.get("block_all"))

    def _credits_for_action(self, action: str) -> int:
        action_key = (action or "").strip().lower()
        if action_key in AI_ACTION_COSTS:
            return int(AI_ACTION_COSTS[action_key]["units"])
        aliases = {
            "email_classification": "categorization",
            "classify": "categorization",
            "summary": "summarization",
            "thread_summarization": "summarization",
            "reply": "reply_drafting",
            "workflow_classification": "categorization",
        }
        mapped = aliases.get(action_key)
        if mapped and mapped in AI_ACTION_COSTS:
            return int(AI_ACTION_COSTS[mapped]["units"])
        return 1

    async def check_credits(self, user_id: str, credits_needed: int, session: AsyncSession) -> bool:
        if await self._is_user_blocked(user_id, session):
            raise PaymentRequiredError("Access blocked by admin policy")
        if await self._has_payment_bypass(user_id, session):
            return True
        result = await session.execute(select(AICredits).where(AICredits.user_id == user_id))
        ai_credits = result.scalar_one_or_none()
        if ai_credits and ai_credits.balance >= credits_needed:
            return True
        raise PaymentRequiredError(f"Insufficient credits: need {credits_needed}")

    async def check_credits_for_ai_action(
        self, user_id: str, action: str, session: AsyncSession
    ) -> bool:
        credits_needed = self._credits_for_action(action)
        return await self.check_credits(
            user_id=user_id, credits_needed=credits_needed, session=session
        )

    async def deduct_credits(
        self, user_id: str, feature: str, credits: int, session: AsyncSession
    ) -> bool:
        """Deduct credits for a feature use"""
        if await self._is_user_blocked(user_id, session):
            logger.warning(f"User {user_id} blocked by admin policy")
            return False
        if await self._has_payment_bypass(user_id, session):
            # Super admin or explicitly bypassed users are not billed.
            return True

        result = await session.execute(select(AICredits).where(AICredits.user_id == user_id))
        ai_credits = result.scalar()

        if not ai_credits or ai_credits.balance < credits:
            logger.warning(f"Insufficient credits for user {user_id}")
            return False

        ai_credits.balance -= credits
        ai_credits.monthly_used += credits
        subscription_result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = subscription_result.scalar_one_or_none()
        if subscription:
            subscription.ai_credits_monthly_used += credits
            subscription.credits_used += credits

        # Update feature-specific counters
        feature_key = (feature or "").lower()
        if feature_key in {"email_classification", "classify", "categorization"}:
            ai_credits.classification_used += credits
        elif feature_key == "action_extraction":
            ai_credits.extraction_used += credits
        elif feature_key in {"thread_summarization", "summarization", "summary"}:
            ai_credits.summarization_used += credits
        elif feature_key == "sentiment_analysis":
            ai_credits.sentiment_analysis_used += credits
        else:
            ai_credits.other_used += credits

        # Log usage
        usage = UsageLog(
            user_id=user_id,
            tenant_id=ai_credits.tenant_id,
            metric=feature,
            quantity=credits,
            action=feature,
            credits_used=credits,
            tokens_used=0,
            timestamp=datetime.utcnow(),
            breakdown={"reason": "feature_use"},
        )
        credit_transaction = CreditTransaction(
            user_id=user_id,
            credits_used=credits,
            source="usage",
        )
        session.add(usage)
        session.add(credit_transaction)
        await session.flush()

        return True

    async def deduct_credits_for_ai_action(
        self, user_id: str, action: str, session: AsyncSession, tokens_used: int = 0
    ) -> Dict[str, Any]:
        credits = self._credits_for_action(action)
        await self.check_credits(user_id=user_id, credits_needed=credits, session=session)
        ok = await self.deduct_credits(
            user_id=user_id, feature=action, credits=credits, session=session
        )
        if not ok:
            raise PaymentRequiredError(f"Insufficient credits: need {credits}")
        return {
            "success": True,
            "credits_used": credits,
            "tokens_used": tokens_used,
        }

    async def add_credits(
        self, user_id: str, credits: int, reason: str, session: AsyncSession
    ) -> bool:
        """Add credits to a user account"""

        result = await session.execute(select(AICredits).where(AICredits.user_id == user_id))
        ai_credits = result.scalar()

        if not ai_credits:
            logger.error(f"No AI credits account for user {user_id}")
            return False

        ai_credits.balance += credits

        # Log the addition
        usage = UsageLog(
            user_id=user_id,
            tenant_id=ai_credits.tenant_id,
            metric="credit_addition",
            quantity=-credits,  # Negative for additions
            action="credit_addition",
            credits_used=0,
            tokens_used=0,
            timestamp=datetime.utcnow(),
            breakdown={"reason": reason},
        )
        credit_transaction = CreditTransaction(
            user_id=user_id,
            credits_added=credits,
            source=reason,
        )
        session.add(usage)
        session.add(credit_transaction)
        await session.flush()

        return True

    async def get_credits(self, user_id: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
        """Get current credit balance"""

        result = await session.execute(select(AICredits).where(AICredits.user_id == user_id))
        ai_credits = result.scalar()

        if not ai_credits:
            return None

        return {
            "ai_credits": ai_credits.to_dict(),
            "balance_usd": round(ai_credits.balance * 0.004, 2),
            "credit_definition": "1 AI Credit = 1 email processed (or 1,000 tokens)",
        }

    async def deduct_outbound_credits(
        self, user_id: str, emails_count: int, session: AsyncSession
    ) -> bool:
        """Deduct outbound credits for sending emails"""

        result = await session.execute(
            select(OutboundCredits).where(OutboundCredits.user_id == user_id)
        )
        outbound = result.scalar()

        if not outbound or outbound.balance < emails_count:
            logger.warning(f"Insufficient outbound credits for user {user_id}")
            return False

        outbound.balance -= emails_count
        outbound.monthly_used += emails_count

        usage = UsageLog(
            user_id=user_id,
            tenant_id=outbound.tenant_id,
            metric="outbound_email",
            quantity=emails_count,
            breakdown={"reason": "campaign_send"},
        )

        session.add(usage)
        await session.flush()

        return True


class FeatureGatingService:
    """Enforce feature access based on subscription tier and credits"""

    FEATURE_ALIASES: Dict[str, List[str]] = {
        "email_classification": [
            "email_classification",
            "email_categorization",
            "categorization",
            "classify",
        ],
        "action_extraction": ["action_extraction"],
        "thread_summarization": [
            "thread_summarization",
            "email_summaries",
            "summarization",
            "summary",
        ],
        "sentiment_analysis": ["sentiment_analysis"],
        "shared_inbox": ["shared_inbox", "shared_inboxes", "team_shared_inbox"],
        "workflow_automation": [
            "workflow_automation",
            "workflows",
            "workflow_builder",
            "unlimited_workflows",
        ],
        "crm_sync": ["crm_sync", "crm_lite", "auto_crm"],
        "advanced_analytics": ["advanced_analytics", "analytics_dashboard", "dashboard"],
        "api_access": ["api_access"],
        "outbound_campaigns": ["outbound_campaigns", "outbound_assistant"],
    }

    @classmethod
    def _normalize_feature(cls, feature: str) -> str:
        f = (feature or "").strip().lower()
        for canonical, aliases in cls.FEATURE_ALIASES.items():
            if f == canonical or f in aliases:
                return canonical
        return f

    @classmethod
    def _feature_matches_override(
        cls, override_map: Dict[str, Any], feature: str
    ) -> Optional[bool]:
        if not override_map:
            return None
        normalized = cls._normalize_feature(feature)
        # Accept both exact and alias keys in stored overrides.
        for key, value in override_map.items():
            if cls._normalize_feature(str(key)) == normalized:
                return bool(value)
        return None

    @classmethod
    def _has_plan_feature(cls, features: Dict[str, Any], feature: str) -> bool:
        normalized = cls._normalize_feature(feature)
        aliases = cls.FEATURE_ALIASES.get(normalized, [normalized])
        return any(bool(features.get(k)) for k in aliases)

    async def can_access_feature(self, user_id: str, feature: str, session: AsyncSession) -> bool:
        """Check if user can access a feature"""
        user_row = await session.execute(select(User).where(User.id == user_id))
        user = user_row.scalar_one_or_none()
        allowed_admins = {
            e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()
        }
        if user and user.email and user.email.lower() in allowed_admins:
            return True

        override_setting = await session.get(SystemSetting, "user_access_overrides_v1")
        override = {}
        if override_setting and override_setting.value and user and user.email:
            try:
                payload = json.loads(override_setting.value)
                override = (payload or {}).get(user.email.lower(), {}) or {}
            except Exception:
                override = {}

        if override.get("block_all"):
            return False
        if override.get("allow_all"):
            return True
        feature_overrides = override.get("feature_overrides") or {}
        override_decision = self._feature_matches_override(feature_overrides, feature)
        if override_decision is not None:
            return override_decision

        # Get subscription
        result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        subscription = result.scalar()

        plan_id = None
        plan_features: Dict[str, Any] = {}
        has_active_subscription = bool(subscription and subscription.status == "active")

        if subscription:
            plan_id = subscription.plan_id
            if isinstance(subscription.features, dict) and subscription.features:
                plan_features = subscription.features
            else:
                plan_features = SUBSCRIPTION_PLANS.get(plan_id, {}).get("features", {}) or {}
        elif user:
            # Fallback for legacy users that may have plan fields but missing Subscription row.
            plan_id = (getattr(user, "plan", None) or "personal").lower()
            plan_features = SUBSCRIPTION_PLANS.get(plan_id, {}).get("features", {}) or {}

        normalized_feature = self._normalize_feature(feature)
        if normalized_feature in {
            "email_classification",
            "action_extraction",
            "thread_summarization",
            "sentiment_analysis",
        }:
            # AI capability availability is plan-based. Credit balance enforcement happens in CreditService.
            if has_active_subscription:
                return True
            return plan_id in SUBSCRIPTION_PLANS

        if normalized_feature in {
            "shared_inbox",
            "workflow_automation",
            "crm_sync",
            "advanced_analytics",
            "api_access",
            "outbound_campaigns",
        }:
            return self._has_plan_feature(plan_features, normalized_feature)

        # Unknown features are allowed by default to avoid hard failures on newly introduced flags.
        return True

    async def enforce_team_limit(self, user_id: str, session: AsyncSession) -> bool:
        """Check if user can add more team members"""

        result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        subscription = result.scalar()

        if not subscription:
            return False

        return (subscription.seats_current or 0) < (
            subscription.seats_max or subscription.seats_included or 0
        )
