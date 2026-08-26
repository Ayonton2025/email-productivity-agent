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


@router.get("/credits", response_model=Optional[CreditsResponse])
async def get_credits(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Get user's current credit balance"""
    try:
        credits = await credit_service.get_credits(current_user.id, session)
        return credits

    except Exception as e:
        logger.error(f"Error getting credits: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve credits")


@router.post("/credits/topup")
async def initialize_credit_topup(
    request: CreditTopupRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Initialize a credit top-up purchase (step 1)"""
    try:
        _enforce_ip_rate_limit(http_request, "billing_topup", max_requests=10, window_seconds=60)
        # Validate request
        if request.credits <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credits must be a positive value")

        amount_usd = payment_service.get_credit_pack_price_usd(request.credits)
        if amount_usd is None:
            supported = ", ".join(str(v) for v in sorted(CREDIT_PACK_PRICING_USD.keys()))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid credit pack. Supported packs: {supported}",
            )

        country_code = request.country_code or "US"
        currency, conversion_rate = await payment_service.get_currency_for_country(country_code)
        local_amount = amount_usd * conversion_rate
        amount_minor = int(round(local_amount * 100))  # smallest currency unit

        result = await payment_service.initialize_credit_purchase(
            user_id=current_user.id,
            email=request.email,
            credits=request.credits,
            amount_minor=amount_minor,
            currency=currency,
            amount_usd=amount_usd,
            session=session,
        )

        await session.commit()

        if result.get("success"):
            return {
                "success": True,
                "authorization_url": result["authorization_url"],
                "transaction_id": result["transaction_id"],
                "reference": result["reference"],
                "amount": amount_usd,
                "currency": currency,
                "credits": request.credits,
                "credit_definition": "1 AI Credit = 1 email processed (or 1,000 tokens)",
            }
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing credit topup: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initialize payment")


@router.get("/credits/topup/{reference}")
async def check_topup_status(
    reference: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)
):
    """Check status of a credit top-up (step 2)"""
    try:
        from sqlalchemy import select

        tx_result = await session.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.payment_reference == reference,
                PaymentTransaction.user_id == current_user.id,
                PaymentTransaction.charge_type == "credit_topup",
            )
        )
        transaction = tx_result.scalar_one_or_none()
        if not transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Top-up reference not found")

        if transaction.payment_method != "paystack":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported payment method for top-up verification"
            )

        result = await payment_service.paystack.verify_payment(reference)

        if result.get("success"):
            return {
                "success": True,
                "status": "completed",
                "amount": result["amount"] / 100,
                "message": "Payment completed successfully",
            }
        else:
            return {"success": False, "status": "pending", "message": "Payment still pending"}

    except Exception as e:
        logger.error(f"Error checking topup status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check payment status")


# ============================
# Webhook Endpoints
# ============================
