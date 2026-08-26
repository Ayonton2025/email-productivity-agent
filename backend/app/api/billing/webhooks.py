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


@router.post("/webhook/paystack")
async def paystack_webhook(request: Request, session: AsyncSession = Depends(get_db)):
    """Handle Paystack payment webhook for both credit top-ups and subscription upgrades"""
    try:
        body = await request.body()
        signature = request.headers.get("x-paystack-signature")
        if settings.PAYSTACK_SECRET_KEY:
            computed = hmac.new(settings.PAYSTACK_SECRET_KEY.encode("utf-8"), body, hashlib.sha512).hexdigest()
            if not signature or not hmac.compare_digest(signature, computed):
                logger.warning("Invalid Paystack webhook signature")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
        else:
            logger.warning("PAYSTACK_SECRET_KEY not set; skipping signature verification")

        payload = json.loads(body.decode("utf-8"))
        event_name = payload.get("event")
        if event_name == "charge.success":
            reference = payload.get("data", {}).get("reference")

            if reference:
                # Find transaction by reference
                from sqlalchemy import select

                result = await session.execute(
                    select(PaymentTransaction).where(PaymentTransaction.payment_reference == reference)
                )
                transaction = result.scalar()

                if not transaction:
                    logger.warning(f"Transaction not found for reference: {reference}")
                    return {"success": False}

                # Handle based on transaction type
                if transaction.charge_type == "subscription_upgrade":
                    result = await payment_service.process_upgrade_payment(transaction.id, session)
                else:
                    # Credit top-up
                    result = await payment_service.handle_payment_callback(reference, session)

                await session.commit()

                if result.get("success"):
                    logger.info(f"✅ Paystack payment processed: {reference}")
                    return {"success": True}

        elif event_name == "subscription.create":
            email = payload.get("data", {}).get("customer", {}).get("email")
            if email:
                user_row = await session.execute(select(User).where(User.email == email))
                user = user_row.scalar_one_or_none()
                if user:
                    user.subscription_status = "active"
                    await session.commit()
            return {"success": True}

        elif event_name == "subscription.disable":
            email = payload.get("data", {}).get("customer", {}).get("email")
            if email:
                user_row = await session.execute(select(User).where(User.email == email))
                user = user_row.scalar_one_or_none()
                if user:
                    user.subscription_status = "cancelled"
                    await session.commit()
            return {"success": True}

        return {"success": False}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Paystack webhook: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/webhook/paypal")
async def paypal_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle PayPal webhook events (CHECKOUT.ORDER.COMPLETED, etc.)"""
    try:
        payload = await request.json()
        event_type = payload.get("event_type")
        resource = payload.get("resource", {})

        logger.info(f"📨 PayPal Webhook: {event_type}")

        if event_type in {"CHECKOUT.ORDER.COMPLETED", "PAYMENT.SALE.COMPLETED"}:
            order_id = resource.get("id") or resource.get("supplementary_data", {}).get("related_ids", {}).get(
                "order_id"
            )

            if order_id:
                result = await db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.payment_reference == order_id, PaymentTransaction.payment_method == "paypal"
                    )
                )
                transaction = result.scalar_one_or_none()

                if transaction:
                    res = await payment_service.process_upgrade_payment(transaction.id, db)
                    await db.commit()
                    if res.get("success"):
                        logger.info(f"✅ PayPal payment processed: {order_id}")
                        return {"success": True}
                else:
                    logger.warning(f"PayPal transaction not found: {order_id}")

        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            subscriber = resource.get("subscriber", {})
            email = subscriber.get("email_address")
            if email:
                user_row = await db.execute(select(User).where(User.email == email))
                user = user_row.scalar_one_or_none()
                if user:
                    user.subscription_status = "active"
                    await db.commit()
            return {"success": True}

        if event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            subscriber = resource.get("subscriber", {})
            email = subscriber.get("email_address")
            if email:
                user_row = await db.execute(select(User).where(User.email == email))
                user = user_row.scalar_one_or_none()
                if user:
                    user.subscription_status = "cancelled"
                    await db.commit()
            return {"success": True}

        return {"success": False}

    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/webhook/coinbase")
async def coinbase_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Coinbase Commerce webhook events.
    Expected event: charge:confirmed
    """
    try:
        payload = await request.json()
        event_type = payload.get("event", {}).get("type")
        data = payload.get("event", {}).get("data", {}) or {}
        charge_id = data.get("id")

        logger.info(f"📨 Coinbase Webhook: {event_type} charge_id={charge_id}")

        if event_type in {"charge:confirmed", "charge:resolved"} and charge_id:
            from sqlalchemy import text

            result = await db.execute(
                text(
                    "SELECT id FROM payment_transactions "
                    "WHERE payment_method = 'crypto' "
                    "AND payment_metadata::text LIKE :charge_pattern "
                    "LIMIT 1"
                ),
                {"charge_pattern": f"%{charge_id}%"},
            )
            row = result.first()
            if row:
                transaction_id = row[0]
                res = await payment_service.process_upgrade_payment(transaction_id, db)
                await db.commit()
                if res.get("success"):
                    logger.info(f"✅ Coinbase payment processed: {charge_id}")
                    return {"success": True}
                return {"success": False, "message": res.get("message")}
            logger.warning(f"Coinbase transaction not found for charge_id={charge_id}")

        return {"success": False}
    except Exception as e:
        logger.error(f"Error processing Coinbase webhook: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================
# Feature Gating Endpoint
# ============================
