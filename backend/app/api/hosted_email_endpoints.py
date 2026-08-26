"""
Hosted/internal email endpoints (Option A integration).
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_current_user, logger
from app.models.database import UserEmailAccount, get_db
from app.models.hosted_email_models import HostedEmailSendLog
from app.models.user_models import User
from app.services.hosted_email_provider_service import HostedEmailProviderService

router = APIRouter(prefix="/hosted-email", tags=["hosted-email"])
hosted_service = HostedEmailProviderService()


class HostedProvisionRequest(BaseModel):
    local_part: str = Field(..., min_length=3, max_length=32)
    display_name: Optional[str] = Field(default=None, max_length=255)


class HostedSignupRequest(BaseModel):
    local_part: str = Field(..., min_length=3, max_length=32)
    full_name: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)


def _generate_app_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(max(12, length)))


@router.get("/availability")
async def check_hosted_email_availability(
    local_part: str = Query(..., min_length=3, max_length=32),
    db: AsyncSession = Depends(get_db),
):
    if not hosted_service.is_enabled():
        raise HTTPException(status_code=503, detail="Hosted email is not enabled")

    valid, error = hosted_service.validate_local_part(local_part)
    if not valid:
        return {"available": False, "error": error}

    email = hosted_service.build_email_address(local_part)
    available = await hosted_service.check_address_available(email=email, session=db)
    return {
        "available": available,
        "email": email,
        "domain": settings.HOSTED_EMAIL_DOMAIN,
    }


@router.post("/provision")
async def provision_hosted_email_for_user(
    request: HostedProvisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not hosted_service.is_enabled():
        raise HTTPException(status_code=503, detail="Hosted email is not enabled")

    try:
        result = await hosted_service.provision_mailbox_for_user(
            session=db,
            user_id=current_user.id,
            local_part=request.local_part,
            display_name=request.display_name or current_user.full_name,
        )
        account = result["account"]
        provisioning = result["provisioning"]
        return {
            "success": True,
            "account": account.to_dict(),
            "provisioning": provisioning.to_dict(),
            "provider": settings.HOSTED_EMAIL_PROVIDER,
            "domain": settings.HOSTED_EMAIL_DOMAIN,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Hosted mailbox provisioning failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to provision hosted mailbox")


@router.post("/signup")
async def signup_with_hosted_email(
    request: HostedSignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Lightweight flow: user chooses "Get Bylix Email".
    System still creates auth account + hosted mailbox under the hood.
    """
    if not hosted_service.is_enabled():
        raise HTTPException(status_code=503, detail="Hosted email is not enabled")
    if not settings.HOSTED_EMAIL_ALLOW_PUBLIC_SIGNUP:
        raise HTTPException(status_code=403, detail="Hosted public signup is disabled")

    valid, error = hosted_service.validate_local_part(request.local_part)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    hosted_email = hosted_service.build_email_address(request.local_part)
    available = await hosted_service.check_address_available(hosted_email, db)
    if not available:
        raise HTTPException(status_code=400, detail="Requested email is already taken")

    user_password = request.password or _generate_app_password()

    # Ensure no existing user with same login email
    existing_result = await db.execute(select(User).where(User.email == hosted_email))
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = User(
        email=hosted_email,
        full_name=request.full_name,
        is_verified=True,
        is_active=True,
    )
    user.set_password(user_password)
    db.add(user)
    await db.flush()

    try:
        provision_result = await hosted_service.provision_mailbox_for_user(
            session=db,
            user_id=user.id,
            local_part=request.local_part,
            display_name=request.full_name,
        )
    except Exception:
        await db.rollback()
        raise

    access_token = create_access_token(data={"user_id": user.id})

    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
        },
        "account": provision_result["account"].to_dict(),
        "domain": settings.HOSTED_EMAIL_DOMAIN,
        "temporary_password": None if request.password else user_password,
    }


@router.get("/limits")
async def get_hosted_email_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(
        select(UserEmailAccount).where(
            and_(
                UserEmailAccount.user_id == current_user.id,
                UserEmailAccount.email_account_type == "hosted_internal",
                UserEmailAccount.is_active == True,
            )
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="No active hosted email account found")

    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    day_end = day_start + timedelta(days=1)

    sent_today_q = await db.execute(
        select(func.count(HostedEmailSendLog.id)).where(
            and_(
                HostedEmailSendLog.account_id == account.id,
                HostedEmailSendLog.created_at >= day_start,
                HostedEmailSendLog.created_at < day_end,
                HostedEmailSendLog.blocked == False,
            )
        )
    )
    blocked_today_q = await db.execute(
        select(func.count(HostedEmailSendLog.id)).where(
            and_(
                HostedEmailSendLog.account_id == account.id,
                HostedEmailSendLog.created_at >= day_start,
                HostedEmailSendLog.created_at < day_end,
                HostedEmailSendLog.blocked == True,
            )
        )
    )

    sent_today = int(sent_today_q.scalar_one() or 0)
    blocked_today = int(blocked_today_q.scalar_one() or 0)
    limit = int(account.send_limit_daily or settings.HOSTED_EMAIL_DAILY_SEND_LIMIT or 0)
    remaining = None if limit <= 0 else max(0, limit - sent_today)

    return {
        "success": True,
        "account_id": account.id,
        "email": account.email,
        "daily_limit": limit,
        "sent_today": sent_today,
        "blocked_today": blocked_today,
        "remaining_today": remaining,
        "domain_daily_limit": int(settings.HOSTED_EMAIL_DOMAIN_DAILY_SEND_LIMIT or 0),
        "spam_threshold": float(settings.HOSTED_EMAIL_SPAM_SCORE_BLOCK_THRESHOLD or 0.75),
    }
