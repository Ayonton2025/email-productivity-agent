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

from fastapi import APIRouter, HTTPException, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import hashlib
import hmac
import json

from app.models.database import get_db, User
from app.models.billing_models import (
    Subscription, SUBSCRIPTION_PLANS, PaymentTransaction, CREDIT_PACK_PRICING_USD
)
from app.services.billing_service import (
    SubscriptionService, PaymentService, CreditService, FeatureGatingService
)
from app.core.security import get_current_user, logger
from app.core.config import settings

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
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests, please retry shortly.")
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

class SubscriptionResponse(BaseModel):
    id: str
    plan_id: str
    plan_name: str
    status: str
    current_period_end: datetime
    ai_credits_monthly: int
    ai_credits_used: int
    outbound_credits_monthly: int
    outbound_credits_used: int
    team_members_limit: int
    team_members_current: int

    class Config:
        from_attributes = True


class UpgradeRequest(BaseModel):
    plan_id: str
    payment_method: Optional[str] = "auto"  # auto by default; user chooses at hosted checkout
    country_code: Optional[str] = None  # ISO 2-letter code for region-aware routing
    prefer_local_currency: Optional[bool] = False  # Default false to preserve exact USD website pricing


class PaymentMethodUpdateRequest(BaseModel):
    payment_method: str


class CouponRequest(BaseModel):
    code: str


class CreditsResponse(BaseModel):
    ai_credits: dict
    balance_usd: float


class CreditTopupRequest(BaseModel):
    credits: int  # Number of credits to purchase
    email: str  # Email for payment
    country_code: Optional[str] = None  # ISO 2-letter code for currency routing


class AvailablePlansResponse(BaseModel):
    plans: dict


# ============================
# Subscription Endpoints
# ============================

@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get user's current subscription"""
    try:
        subscription = await subscription_service.get_subscription(
            current_user.id, session
        )
        
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
            team_members_current=subscription.seats_current or 0
        )
    
    except Exception as e:
        logger.error(f"Error getting subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription"
        )


@router.post("/upgrade")
async def upgrade_subscription(
    http_request: Request,
    request: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Initiate upgrade: create payment session or perform immediate free upgrade
    
    Supports multiple payment methods:
    - Paystack: card, mpesa, bank_transfer, mobile_money, ussd, qr
    - PayPal: card, paypal wallet, bank transfer
    """
    try:
        _enforce_ip_rate_limit(http_request, "billing_upgrade", max_requests=8, window_seconds=60)
        logger.info(f"💳 [Billing] Upgrade request: user={current_user.id}, plan={request.plan_id}, method={request.payment_method}")
        
        if request.plan_id not in SUBSCRIPTION_PLANS:
            logger.error(f"❌ [Billing] Invalid plan: {request.plan_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan: {request.plan_id}"
            )

        plan = SUBSCRIPTION_PLANS[request.plan_id]
        logger.info(f"✅ [Billing] Plan found: {plan.get('name')} (${plan.get('price', 0)})")

        # If plan is free, immediately upgrade without payment
        if plan.get("price", 0) == 0:
            logger.info(f"🔄 [Billing] Free upgrade to {request.plan_id}")
            subscription = await subscription_service.upgrade_subscription(
                current_user.id, request.plan_id, session
            )
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
                    team_members_current=subscription.seats_current or 0
                ).dict()
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

        logger.info(f"💰 [Billing] Creating payment session: method={payment_method}, amount=${plan.get('price')}, country={country_code}")
        
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
            logger.error(f"❌ [Billing] Payment service returned None")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment service error"
            )

        # Persist transaction if created inside service
        await session.commit()

        if result.get("success"):
            logger.info(f"✅ [Billing] Payment session created successfully")
            # Return session data for frontend to redirect
            response = {
                k: v for k, v in result.items() 
                if k in (
                    "checkout_url", "authorization_url", 
                    "reference", "amount", "plan_id", "approval_url", 
                    "order_id", "processor", "payment_method", "currency",
                    "display_amount", "display_currency",
                    "currency_fallback_applied", "currency_fallback_reason"
                )
            }
            response.update({"success": True})
            return response
        else:
            error_msg = result.get("message", "Failed to initiate payment")
            logger.error(f"❌ [Billing] Payment service error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Billing] Upgrade error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate upgrade"
        )


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
            "preferred_method": methods[0]["id"] if methods else "card"
        }
    except Exception as e:
        logger.error(f"Error getting payment methods: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment methods"
        )


@router.get("/payment-methods")
async def get_default_payment_methods():
    """Get default payment methods (global coverage)"""
    try:
        methods = payment_service.get_available_payment_methods("US")
        return {
            "success": True,
            "payment_methods": methods
        }
    except Exception as e:
        logger.error(f"Error getting payment methods: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment methods"
        )


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )


@router.put("/payment-method")
async def update_payment_method(
    request: PaymentMethodUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment method"
        )


@router.get("/history")
async def get_billing_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Compatibility endpoint used by frontend paymentService.getBillingHistory."""
    try:
        query = (
            select(PaymentTransaction)
            .where(PaymentTransaction.user_id == current_user.id)
            .order_by(desc(PaymentTransaction.attempted_at))
            .limit(limit)
        )
        result = await session.execute(query)
        transactions = result.scalars().all()
        return {
            "success": True,
            "history": [
                {
                    "id": tx.id,
                    "amount_usd": float(tx.amount_usd or 0),
                    "currency": tx.currency,
                    "payment_method": tx.payment_method,
                    "status": tx.status,
                    "charge_type": tx.charge_type,
                    "reference_id": tx.reference_id,
                    "payment_reference": tx.payment_reference,
                    "attempted_at": tx.attempted_at.isoformat() if tx.attempted_at else None,
                    "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
                }
                for tx in transactions
            ],
        }
    except Exception as e:
        logger.error(f"Error getting billing history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get billing history"
        )


@router.get("/admin/overview")
async def get_admin_overview(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Super admin dashboard metrics."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    total_users = await session.scalar(select(func.count()).select_from(User))
    total_payments = await session.scalar(select(func.count()).select_from(PaymentTransaction))
    completed_payments = await session.scalar(
        select(func.count()).select_from(PaymentTransaction).where(PaymentTransaction.status == "completed")
    )
    pending_payments = await session.scalar(
        select(func.count()).select_from(PaymentTransaction).where(PaymentTransaction.status == "pending")
    )
    failed_payments = await session.scalar(
        select(func.count()).select_from(PaymentTransaction).where(PaymentTransaction.status == "failed")
    )
    revenue_usd = await session.scalar(
        select(func.coalesce(func.sum(PaymentTransaction.amount_usd), 0.0))
        .where(PaymentTransaction.status == "completed")
    )

    return {
        "success": True,
        "metrics": {
            "total_users": int(total_users or 0),
            "total_payments": int(total_payments or 0),
            "completed_payments": int(completed_payments or 0),
            "pending_payments": int(pending_payments or 0),
            "failed_payments": int(failed_payments or 0),
            "revenue_usd": float(revenue_usd or 0.0),
        },
    }


@router.get("/admin/transactions")
async def get_admin_transactions(
    limit: int = 200,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Super admin transaction list."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    rows = await session.execute(
        select(PaymentTransaction).order_by(desc(PaymentTransaction.attempted_at)).limit(limit)
    )
    txs = rows.scalars().all()

    return {
        "success": True,
        "transactions": [
            {
                "id": tx.id,
                "user_id": tx.user_id,
                "amount_usd": float(tx.amount_usd or 0.0),
                "currency": tx.currency,
                "payment_method": tx.payment_method,
                "status": tx.status,
                "charge_type": tx.charge_type,
                "reference_id": tx.reference_id,
                "payment_reference": tx.payment_reference,
                "payment_metadata": tx.payment_metadata or {},
                "attempted_at": tx.attempted_at.isoformat() if tx.attempted_at else None,
                "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
            }
            for tx in txs
        ],
    }


@router.get("/admin/reports/revenue-by-currency")
async def get_revenue_by_currency(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Super admin currency analytics report."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    rows = await session.execute(
        select(
            PaymentTransaction.currency,
            func.count().label("payments"),
            func.coalesce(func.sum(PaymentTransaction.amount_usd), 0.0).label("revenue_usd"),
        )
        .where(PaymentTransaction.status == "completed")
        .group_by(PaymentTransaction.currency)
        .order_by(desc(func.coalesce(func.sum(PaymentTransaction.amount_usd), 0.0)))
    )

    report = []
    for currency, payments, revenue_usd in rows.all():
        report.append(
            {
                "currency": currency or "USD",
                "payments": int(payments or 0),
                "revenue_usd": float(revenue_usd or 0.0),
            }
        )

    return {"success": True, "report": report}


def _coupon_catalog() -> dict:
    return {
        "SAVE10": {"code": "SAVE10", "discount_percent": 10, "description": "10% off"},
        "SAVE20": {"code": "SAVE20", "discount_percent": 20, "description": "20% off"},
    }


@router.post("/coupon/validate")
async def validate_coupon(request: CouponRequest):
    """Compatibility endpoint used by frontend paymentService.validateCoupon."""
    code = (request.code or "").strip().upper()
    coupon = _coupon_catalog().get(code)
    if not coupon:
        return {"valid": False, "message": "Invalid coupon code"}
    return {"valid": True, "coupon": coupon}


@router.post("/coupon/apply")
async def apply_coupon(
    request: CouponRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Compatibility endpoint used by frontend paymentService.applyCoupon."""
    code = (request.code or "").strip().upper()
    coupon = _coupon_catalog().get(code)
    if not coupon:
        raise HTTPException(status_code=400, detail="Invalid coupon code")

    subscription = await subscription_service.get_subscription(current_user.id, session)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    features = dict(subscription.features or {})
    features["applied_coupon"] = coupon
    subscription.features = features
    subscription.updated_at = datetime.utcnow()
    await session.commit()

    return {
        "success": True,
        "message": f"Coupon {coupon['code']} applied",
        "coupon": coupon,
    }


# ============================
# Credits Endpoints
# ============================

@router.get("/credits", response_model=Optional[CreditsResponse])
async def get_credits(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get user's current credit balance"""
    try:
        credits = await credit_service.get_credits(current_user.id, session)
        return credits
    
    except Exception as e:
        logger.error(f"Error getting credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credits"
        )


@router.post("/credits/topup")
async def initialize_credit_topup(
    request: CreditTopupRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Initialize a credit top-up purchase (step 1)"""
    try:
        _enforce_ip_rate_limit(http_request, "billing_topup", max_requests=10, window_seconds=60)
        # Validate request
        if request.credits <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credits must be a positive value"
            )

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
            session=session
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message")
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing credit topup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize payment"
        )


@router.get("/credits/topup/{reference}")
async def check_topup_status(
    reference: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Check status of a credit top-up (step 2)"""
    try:
        from sqlalchemy import select
        tx_result = await session.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.payment_reference == reference,
                PaymentTransaction.user_id == current_user.id,
                PaymentTransaction.charge_type == "credit_topup"
            )
        )
        transaction = tx_result.scalar_one_or_none()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Top-up reference not found"
            )

        if transaction.payment_method != "paystack":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported payment method for top-up verification"
            )

        result = await payment_service.paystack.verify_payment(reference)
        
        if result.get("success"):
            return {
                "success": True,
                "status": "completed",
                "amount": result["amount"] / 100,
                "message": "Payment completed successfully"
            }
        else:
            return {
                "success": False,
                "status": "pending",
                "message": "Payment still pending"
            }
    
    except Exception as e:
        logger.error(f"Error checking topup status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check payment status"
        )


# ============================
# Webhook Endpoints
# ============================

@router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db)
):
    """Handle Paystack payment webhook for both credit top-ups and subscription upgrades"""
    try:
        body = await request.body()
        signature = request.headers.get("x-paystack-signature")
        if settings.PAYSTACK_SECRET_KEY:
            computed = hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
                body,
                hashlib.sha512
            ).hexdigest()
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
                    select(PaymentTransaction).where(
                        PaymentTransaction.payment_reference == reference
                    )
                )
                transaction = result.scalar()
                
                if not transaction:
                    logger.warning(f"Transaction not found for reference: {reference}")
                    return {"success": False}
                
                # Handle based on transaction type
                if transaction.charge_type == "subscription_upgrade":
                    result = await payment_service.process_upgrade_payment(
                        transaction.id, session
                    )
                else:
                    # Credit top-up
                    result = await payment_service.handle_payment_callback(
                        reference, session
                    )
                
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
async def paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle PayPal webhook events (CHECKOUT.ORDER.COMPLETED, etc.)"""
    try:
        payload = await request.json()
        event_type = payload.get("event_type")
        resource = payload.get("resource", {})
        
        logger.info(f"📨 PayPal Webhook: {event_type}")
        
        if event_type in {"CHECKOUT.ORDER.COMPLETED", "PAYMENT.SALE.COMPLETED"}:
            order_id = resource.get("id") or resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")

            if order_id:
                result = await db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.payment_reference == order_id,
                        PaymentTransaction.payment_method == "paypal"
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
async def coinbase_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
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

@router.get("/features/{feature_name}")
async def check_feature_access(
    feature_name: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
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
        can_access = await gating_service.can_access_feature(
            current_user.id, feature_name, session
        )
        
        return {
            "feature": feature_name,
            "can_access": can_access,
            "user_id": current_user.id
        }
    
    except Exception as e:
        logger.error(f"Error checking feature access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check feature access"
        )


@router.get("/features")
async def get_available_features(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get all available features and their access status"""
    try:
        if _is_super_admin(current_user):
            merged = {}
            for _, cfg in SUBSCRIPTION_PLANS.items():
                for k, v in (cfg.get("features") or {}).items():
                    merged[k] = bool(v) or merged.get(k, False)
            return {"plan": "super_admin", "plan_name": "Super Admin", "features": merged, "payment_bypass": True}

        subscription = await subscription_service.get_subscription(
            current_user.id, session
        )
        
        if not subscription:
            return {"features": {}, "plan": None}
        
        plan = SUBSCRIPTION_PLANS.get(subscription.plan_id, {})
        features = plan.get("features", {})
        
        return {
            "plan": subscription.plan_id,
            "plan_name": subscription.plan_name,
            "features": features
        }
    
    except Exception as e:
        logger.error(f"Error getting features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve features"
        )
