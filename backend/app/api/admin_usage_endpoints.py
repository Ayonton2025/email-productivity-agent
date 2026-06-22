from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import get_current_user
from app.models.database import SystemSetting, User, UserEmailAccount, get_db
from app.models.billing_models import SUBSCRIPTION_PLANS, Subscription, AICredits
from app.services.billing_service import FeatureGatingService


router = APIRouter(prefix="/api/v1/admin/usage", tags=["admin-usage"])


def _is_super_admin(user: User) -> bool:
    allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
    return bool(user.email and user.email.lower() in allowed)


def _overrides_key() -> str:
    return "user_access_overrides_v1"


def _empty_override() -> dict:
    return {
        "allow_all": False,
        "block_all": False,
        "payment_bypass": False,
        "feature_overrides": {},
        "status_note": "",
        "updated_at": None,
        "updated_by": None,
    }


class UserAccessOverrideUpdate(BaseModel):
    allow_all: bool = False
    block_all: bool = False
    payment_bypass: bool = False
    feature_overrides: dict = {}
    is_active: bool | None = None
    status_note: str | None = None


@router.get("/user-access/{email}/send-readiness")
async def get_user_send_readiness(
    email: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Super-admin: check send readiness prerequisites per user/account."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    email_key = (email or "").strip().lower()
    user_row = await session.execute(select(User).where(User.email == email_key))
    user = user_row.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    accounts_result = await session.execute(
        select(UserEmailAccount).where(UserEmailAccount.user_id == user.id).order_by(
            UserEmailAccount.is_primary.desc(),
            UserEmailAccount.created_at.asc(),
        )
    )
    accounts = list(accounts_result.scalars().all())

    now = datetime.utcnow()
    account_checks = []
    any_campaign_ready = False
    any_reply_ready = False

    for account in accounts:
        has_oauth_token = bool(account.access_token)
        has_password_credentials = bool(account.encrypted_password)
        smtp_configured = bool(account.smtp_host and int(account.smtp_port or 0) > 0)
        token_not_expired = (
            True if not account.token_expires_at else bool(account.token_expires_at > now)
        )
        daily_limit = int(account.send_limit_daily or 0)
        daily_count = int(account.send_count_daily or 0)
        daily_limit_ok = daily_limit <= 0 or daily_count < daily_limit

        issues = []
        if not account.is_active:
            issues.append("account_inactive")
        if not account.sync_enabled:
            issues.append("sync_disabled")
        if not smtp_configured:
            issues.append("smtp_not_configured")
        if not has_password_credentials:
            issues.append("smtp_password_missing")
        if not token_not_expired:
            issues.append("oauth_token_expired")
        if not daily_limit_ok:
            issues.append("daily_send_limit_reached")

        campaign_send_ready = bool(
            account.is_active
            and smtp_configured
            and has_password_credentials
            and daily_limit_ok
        )
        reply_send_ready = bool(
            account.is_active
            and (
                campaign_send_ready
                or (has_oauth_token and token_not_expired)
            )
        )

        any_campaign_ready = any_campaign_ready or campaign_send_ready
        any_reply_ready = any_reply_ready or reply_send_ready

        account_checks.append(
            {
                "id": account.id,
                "email": account.email,
                "provider": account.provider,
                "is_primary": bool(account.is_primary),
                "is_active": bool(account.is_active),
                "sync_enabled": bool(account.sync_enabled),
                "last_sync_status": account.last_sync_status,
                "has_oauth_token": has_oauth_token,
                "has_password_credentials": has_password_credentials,
                "token_not_expired": token_not_expired,
                "smtp_configured": smtp_configured,
                "daily_limit": daily_limit,
                "daily_count": daily_count,
                "daily_limit_ok": daily_limit_ok,
                "campaign_send_ready": campaign_send_ready,
                "reply_send_ready": reply_send_ready,
                "issues": issues,
            }
        )

    celery_enabled = bool(settings.CELERY_ENABLED)
    redis_configured = bool(settings.CELERY_BROKER_URL and settings.CELERY_RESULT_BACKEND)

    overall_campaign_ready = bool(user.is_active and any_campaign_ready and celery_enabled and redis_configured)
    overall_reply_ready = bool(user.is_active and any_reply_ready)

    recommended = next((a for a in account_checks if a["is_primary"] and a["campaign_send_ready"]), None)
    if not recommended:
        recommended = next((a for a in account_checks if a["campaign_send_ready"]), None)

    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": bool(user.is_active),
        },
        "global_checks": {
            "user_active": bool(user.is_active),
            "celery_enabled": celery_enabled,
            "redis_configured": redis_configured,
            "has_accounts": len(account_checks) > 0,
        },
        "overall": {
            "campaign_ready": overall_campaign_ready,
            "reply_ready": overall_reply_ready,
        },
        "recommended_campaign_account_id": recommended["id"] if recommended else None,
        "accounts": account_checks,
    }


@router.post("/dismissals/reset")
async def reset_premium_dismissals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Admin-only: set a global dismissal-reset timestamp which clients read to clear local dismissals."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    key = "premium_prompt_dismissals_reset_at"
    now_iso = datetime.utcnow().isoformat() + "Z"

    # Upsert system setting
    existing = await session.get(SystemSetting, key)
    if existing:
        existing.value = now_iso
        existing.updated_at = datetime.utcnow()
    else:
        obj = SystemSetting()
        obj.key = key
        obj.value = now_iso
        session.add(obj)

    await session.commit()

    return {"success": True, "reset_at": now_iso}


@router.get("/user-access/{email}")
async def get_user_access_profile(
    email: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Super-admin: inspect any user's feature access and system status by email."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    email_key = (email or "").strip().lower()
    user_row = await session.execute(select(User).where(User.email == email_key))
    user = user_row.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub_row = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_row.scalar_one_or_none()
    credits_row = await session.execute(select(AICredits).where(AICredits.user_id == user.id))
    credits = credits_row.scalar_one_or_none()

    setting = await session.get(SystemSetting, _overrides_key())
    raw = {}
    if setting and setting.value:
        try:
            raw = json.loads(setting.value) or {}
        except Exception:
            raw = {}
    override = raw.get(email_key, _empty_override())

    gating = FeatureGatingService()
    feature_candidates = set(
        [
            "email_classification",
            "action_extraction",
            "thread_summarization",
            "sentiment_analysis",
            "shared_inbox",
            "workflow_automation",
            "crm_sync",
            "advanced_analytics",
            "api_access",
        ]
    )
    if sub:
        feature_candidates.update((sub.features or {}).keys())
        feature_candidates.update(SUBSCRIPTION_PLANS.get(sub.plan_id, {}).get("features", {}).keys())

    feature_access = {}
    for feature in sorted(feature_candidates):
        try:
            feature_access[feature] = bool(await gating.can_access_feature(user.id, feature, session))
        except Exception:
            feature_access[feature] = False

    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": bool(user.is_active),
            "is_super_admin": _is_super_admin(user),
        },
        "subscription": {
            "plan_id": getattr(sub, "plan_id", "personal"),
            "status": getattr(sub, "status", "none"),
            "plan_name": getattr(sub, "plan_name", "Free"),
            "features": (sub.features or SUBSCRIPTION_PLANS.get(getattr(sub, "plan_id", "personal"), {}).get("features", {})) if sub else {},
        },
        "credits": credits.to_dict() if credits else None,
        "feature_access": feature_access,
        "override": {**_empty_override(), **(override or {})},
    }


@router.put("/user-access/{email}")
async def update_user_access_profile(
    email: str,
    body: UserAccessOverrideUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Super-admin: allow/limit users and apply payment bypass/feature overrides."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    email_key = (email or "").strip().lower()
    user_row = await session.execute(select(User).where(User.email == email_key))
    user = user_row.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    setting = await session.get(SystemSetting, _overrides_key())
    current_data = {}
    if setting and setting.value:
        try:
            current_data = json.loads(setting.value) or {}
        except Exception:
            current_data = {}

    clean_feature_overrides = {}
    for k, v in (body.feature_overrides or {}).items():
        key = str(k).strip()
        if key:
            clean_feature_overrides[key] = bool(v)

    current_data[email_key] = {
        "allow_all": bool(body.allow_all),
        "block_all": bool(body.block_all),
        "payment_bypass": bool(body.payment_bypass),
        "feature_overrides": clean_feature_overrides,
        "status_note": body.status_note or "",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "updated_by": current_user.email,
    }

    if body.is_active is not None:
        user.is_active = bool(body.is_active)

    if not setting:
        setting = SystemSetting()
        setting.key = _overrides_key()
        session.add(setting)
    setting.value = json.dumps(current_data)
    setting.updated_at = datetime.utcnow()

    await session.commit()
    return {"success": True, "email": email_key, "override": current_data[email_key], "is_active": bool(user.is_active)}


@router.get("/feature-templates")
async def get_feature_templates(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get Plus/Pro/Enterprise feature templates for admin UI"""
    # Only super admins can access this
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    from app.models.billing_models import SUBSCRIPTION_PLANS
    
    templates = {}
    for plan_id in ["plus", "pro", "enterprise"]:
        plan = SUBSCRIPTION_PLANS.get(plan_id)
        if plan:
            templates[plan_id] = {
                "name": plan["name"],
                "features": plan["features"]
            }
    
    return {
        "success": True,
        "templates": templates
    }
