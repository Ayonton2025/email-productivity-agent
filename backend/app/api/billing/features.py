"""
Billing and subscription API endpoints

Routes:
- GET /api/v1/billing/subscription - Get user's current subscription
- POST /api/v1/billing/upgrade - Upgrade subscription plan
- GET /api/v1/billing/credits - Get credit balance
- POST /api/v1/billing/credits/topup - Start credit top-up process
- GET /api/v1/billing/credits/topup/{reference} - Check top-up status
- POST /api/v1/billing/webhook/paystack - Paystack webhook handler
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user, logger
from app.models.billing_models import SUBSCRIPTION_PLANS
from app.models.database import User, get_db
from app.services.billing_service import (
    CreditService,
    FeatureGatingService,
    PaymentService,
    SubscriptionService,
)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

subscription_service = SubscriptionService()
payment_service = PaymentService()
credit_service = CreditService()
gating_service = FeatureGatingService()
_IP_REQUEST_LOG = {}


def _enforce_ip_rate_limit(
    request: Request, key: str, max_requests: int = 20, window_seconds: int = 60
) -> None:
    xff = request.headers.get("x-forwarded-for", "")
    ip = (
        xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")
    )
    now = datetime.utcnow().timestamp()
    bucket_key = f"{key}:{ip}"
    events = _IP_REQUEST_LOG.get(bucket_key, [])
    events = [ts for ts in events if now - ts <= window_seconds]
    if len(events) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please retry shortly.",
        )
    events.append(now)
    _IP_REQUEST_LOG[bucket_key] = events


def _is_super_admin(user: User) -> bool:
    if getattr(user, "is_superuser", False) or getattr(user, "is_admin", False):
        return True
    allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
    return bool(user.email and user.email.lower() in allowed)


# ============================
# Request/Response Models
# ============================


# ============================
# Subscription Endpoints
# ============================


@router.get("/features/{feature_name}")
async def check_feature_access(
    feature_name: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Check if user can access a specific feature"""
    try:
        if _is_super_admin(current_user):
            return {
                "feature": feature_name,
                "can_access": True,
                "user_id": current_user.id,
                "payment_bypass": True,
            }
        can_access = await gating_service.can_access_feature(current_user.id, feature_name, session)

        return {"feature": feature_name, "can_access": can_access, "user_id": current_user.id}

    except Exception as e:
        logger.error(f"Error checking feature access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check feature access",
        )


@router.get("/features")
async def get_available_features(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)
):
    """Get all available features and their access status"""
    try:
        if _is_super_admin(current_user):
            merged = {}
            for _, cfg in SUBSCRIPTION_PLANS.items():
                for k, v in (cfg.get("features") or {}).items():
                    merged[k] = bool(v) or merged.get(k, False)
            return {
                "plan": "super_admin",
                "plan_name": "Super Admin",
                "features": merged,
                "payment_bypass": True,
            }

        subscription = await subscription_service.get_subscription(current_user.id, session)

        if not subscription:
            return {"features": {}, "plan": None}

        plan = SUBSCRIPTION_PLANS.get(subscription.plan_id, {})
        features = plan.get("features", {})

        return {
            "plan": subscription.plan_id,
            "plan_name": subscription.plan_name,
            "features": features,
        }

    except Exception as e:
        logger.error(f"Error getting features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve features"
        )
