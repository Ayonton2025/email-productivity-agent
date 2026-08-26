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

import hashlib
import hmac
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.billing.schemas import (
    AvailablePlansResponse,
    CouponRequest,
    CreditsResponse,
    CreditTopupRequest,
    PaymentMethodUpdateRequest,
    SubscriptionResponse,
    UpgradeRequest,
)
from app.core.config import settings
from app.core.security import get_current_user, logger
from app.models.billing_models import CREDIT_PACK_PRICING_USD, SUBSCRIPTION_PLANS, PaymentTransaction
from app.models.database import User, get_db
from app.services.billing_service import CreditService, FeatureGatingService, PaymentService, SubscriptionService

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

subscription_service = SubscriptionService()
payment_service = PaymentService()
credit_service = CreditService()
gating_service = FeatureGatingService()
_IP_REQUEST_LOG = {}


def _enforce_ip_rate_limit(request: Request, key: str, max_requests: int = 20, window_seconds: int = 60) -> None:
    xff = request.headers.get("x-forwarded-for", "")
    ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")
    now = datetime.utcnow().timestamp()
    bucket_key = f"{key}:{ip}"
    events = _IP_REQUEST_LOG.get(bucket_key, [])
    events = [ts for ts in events if now - ts <= window_seconds]
    if len(events) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests, please retry shortly."
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


@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_subscription(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get user's current subscription"""
    try:
        subscription = await subscription_service.get_subscription(current_user.id, session)

        if not subscription:
            return None

        return SubscriptionResponse(
            id=subscription.id,
            plan_id=subscription.plan_id,
            plan_name=subscription.plan_name,
            status=subscription.status,
            current_period_end=subscription.current_period_end,
            ai_credits_monthly=subscription.ai_credits_monthly_allocation,
            ai_credits_used=subscription.ai_credits_monthly_used,
            outbound_credits_monthly=subscription.outbound_emails_monthly_allocation,
            outbound_credits_used=subscription.outbound_emails_monthly_used,
            team_members_limit=subscription.seats_max or subscription.seats_included or 0,
            team_members_current=subscription.seats_current or 0,
        )

    except Exception as e:
        logger.error(f"Error getting subscription: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve subscription")


@router.post("/upgrade")
async def upgrade_subscription(
    http_request: Request,
    request: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Initiate upgrade: create payment session or perform immediate free upgrade

    Supports multiple payment methods:
    - Paystack: card, mpesa, bank_transfer, mobile_money, ussd, qr
    - PayPal: card, paypal wallet, bank transfer
    """
    try:
        _enforce_ip_rate_limit(http_request, "billing_upgrade", max_requests=8, window_seconds=60)
        logger.info(
            f"💳 [Billing] Upgrade request: user={current_user.id}, plan={request.plan_id}, method={request.payment_method}"
        )

        if request.plan_id not in SUBSCRIPTION_PLANS:
            logger.error(f"❌ [Billing] Invalid plan: {request.plan_id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid plan: {request.plan_id}")

        plan = SUBSCRIPTION_PLANS[request.plan_id]
        logger.info(f"✅ [Billing] Plan found: {plan.get('name')} (${plan.get('price', 0)})")

        # If plan is free, immediately upgrade without payment
        if plan.get("price", 0) == 0:
            logger.info(f"🔄 [Billing] Free upgrade to {request.plan_id}")
            subscription = await subscription_service.upgrade_subscription(current_user.id, request.plan_id, session)
            await session.commit()
            return {
                "success": True,
                "message": f"Upgraded to {subscription.plan_name}",
                "subscription": SubscriptionResponse(
                    id=subscription.id,
                    plan_id=subscription.plan_id,
                    plan_name=subscription.plan_name,
                    status=subscription.status,
                    current_period_end=subscription.current_period_end,
                    ai_credits_monthly=subscription.ai_credits_monthly_allocation,
                    ai_credits_used=subscription.ai_credits_monthly_used,
                    outbound_credits_monthly=subscription.outbound_emails_monthly_allocation,
                    outbound_credits_used=subscription.outbound_emails_monthly_used,
                    team_members_limit=subscription.seats_max or subscription.seats_included or 0,
                    team_members_current=subscription.seats_current or 0,
                ).dict(),
            }

        # Otherwise create a payment session
        payment_method = request.payment_method or "auto"
        # Backwards-compatibility: map legacy frontend values to Paystack-compatible method
        if payment_method == "paystack":
            payment_method = "auto"
        elif payment_method == "stripe":
            payment_method = "card"
        country_code = (request.country_code or "").upper()
        if not country_code:
            xff = http_request.headers.get("x-forwarded-for", "")
            client_ip = xff.split(",")[0].strip() if xff else (http_request.client.host if http_request.client else "")
            country_code = await payment_service.detect_country_code_from_ip(client_ip)

        logger.info(
            f"💰 [Billing] Creating payment session: method={payment_method}, amount=${plan.get('price')}, country={country_code}"
        )

        result = await payment_service.create_upgrade_session(
            user_id=current_user.id,
            user_email=current_user.email,
            plan_id=request.plan_id,
            payment_method=payment_method,
            session=session,
            country_code=country_code,
            frontend_url=None,
            prefer_local_currency=bool(request.prefer_local_currency),
        )

        logger.info(f"📊 [Billing] Payment service response: {result.get('success')}")

        if not result:
            logger.error("❌ [Billing] Payment service returned None")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment service error")

        # Persist transaction if created inside service
        await session.commit()

        if result.get("success"):
            logger.info("✅ [Billing] Payment session created successfully")
            # Return session data for frontend to redirect
            response = {
                k: v
                for k, v in result.items()
                if k
                in (
                    "checkout_url",
                    "authorization_url",
                    "reference",
                    "amount",
                    "plan_id",
                    "approval_url",
                    "order_id",
                    "processor",
                    "payment_method",
                    "currency",
                    "display_amount",
                    "display_currency",
                    "currency_fallback_applied",
                    "currency_fallback_reason",
                )
            }
            response.update({"success": True})
            return response
        else:
            error_msg = result.get("message", "Failed to initiate payment")
            logger.error(f"❌ [Billing] Payment service error: {error_msg}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Billing] Upgrade error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate upgrade")


@router.get("/plans", response_model=AvailablePlansResponse)
async def get_available_plans():
    """Get list of available subscription plans"""
    return AvailablePlansResponse(plans=SUBSCRIPTION_PLANS)


@router.get("/payment-methods/{country_code}")
async def get_payment_methods(country_code: str = "US"):
    """Get available payment methods for a specific country

    Args:
        country_code: ISO 2-letter country code (e.g., KE, NG, GH, US)

    Returns:
        List of available payment methods with metadata
    """
    try:
        methods = payment_service.get_available_payment_methods(country_code)
        return {
            "success": True,
            "country_code": country_code.upper(),
            "payment_methods": methods,
            "preferred_method": methods[0]["id"] if methods else "card",
        }
    except Exception as e:
        logger.error(f"Error getting payment methods: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get payment methods")


@router.get("/payment-methods")
async def get_default_payment_methods():
    """Get default payment methods (global coverage)"""
    try:
        methods = payment_service.get_available_payment_methods("US")
        return {"success": True, "payment_methods": methods}
    except Exception as e:
        logger.error(f"Error getting payment methods: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get payment methods")


@router.post("/cancel")
async def cancel_subscription(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Compatibility endpoint used by frontend paymentService.cancelSubscription."""
    try:
        subscription = await subscription_service.cancel_subscription(current_user.id, session)
        await session.commit()
        return {
            "success": True,
            "message": "Subscription cancelled",
            "subscription": {
                "id": subscription.id,
                "plan_id": subscription.plan_id,
                "status": subscription.status,
                "auto_renew": subscription.auto_renew,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel subscription")


@router.put("/payment-method")
async def update_payment_method(
    request: PaymentMethodUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Compatibility endpoint used by frontend paymentService.updatePaymentMethod."""
    try:
        subscription = await subscription_service.get_subscription(current_user.id, session)
        if not subscription:
            raise HTTPException(status_code=404, detail="No subscription found")
        subscription.payment_method = request.payment_method
        subscription.updated_at = datetime.utcnow()
        await session.commit()
        return {
            "success": True,
            "message": "Payment method updated",
            "payment_method": request.payment_method,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment method: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update payment method")
