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
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.billing.schemas import (
    CouponRequest,
)
from app.core.config import settings
from app.core.security import get_current_user, logger
from app.models.billing_models import PaymentTransaction
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


@router.get("/history")
async def get_billing_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
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
            detail="Failed to get billing history",
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
        select(func.count())
        .select_from(PaymentTransaction)
        .where(PaymentTransaction.status == "completed")
    )
    pending_payments = await session.scalar(
        select(func.count())
        .select_from(PaymentTransaction)
        .where(PaymentTransaction.status == "pending")
    )
    failed_payments = await session.scalar(
        select(func.count())
        .select_from(PaymentTransaction)
        .where(PaymentTransaction.status == "failed")
    )
    revenue_usd = await session.scalar(
        select(func.coalesce(func.sum(PaymentTransaction.amount_usd), 0.0)).where(
            PaymentTransaction.status == "completed"
        )
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
    session: AsyncSession = Depends(get_db),
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
