"""Account endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import GmailConnectionRequest
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user_models import User

router = APIRouter()
# Preserve the established log category for compatibility with operational filters.
logger = get_logger("app.api.endpoints")


@router.get("/email-accounts", response_model=List[Dict[str, Any]])
async def get_user_email_accounts_simple(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get user's connected email accounts"""
    try:
        from sqlalchemy import select

        from app.models.email_models import UserEmailAccount

        result = await db.execute(
            select(UserEmailAccount)
            .where(UserEmailAccount.user_id == current_user.id)
            .order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc())
        )
        accounts = result.scalars().all()
        return [account.to_dict() for account in accounts]

    except Exception as e:
        logger.error(f"Error getting email accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get email accounts")


@router.post("/email-accounts/gmail")
async def connect_gmail_simple(
    auth_data: GmailConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect Gmail account"""
    try:
        from app.models.email_models import UserEmailAccount
        from app.services.email_provider_service import EmailProviderService

        email_provider_service = EmailProviderService()

        success = await email_provider_service.authenticate_gmail_with_token(
            auth_data.access_token, auth_data.refresh_token
        )

        if success:
            # Store email account in database
            email_account = UserEmailAccount(
                user_id=current_user.id,
                provider="gmail",
                email=auth_data.email,
                access_token=auth_data.access_token,
                refresh_token=auth_data.refresh_token,
                token_expiry=auth_data.token_expiry,
                is_primary=True,
            )

            db.add(email_account)
            await db.commit()
            await db.refresh(email_account)

            return {
                "status": "success",
                "message": "Gmail account connected successfully",
                "account": email_account.to_dict(),
            }
        else:
            raise HTTPException(status_code=400, detail="Gmail authentication failed")

    except Exception as e:
        logger.error(f"Error connecting Gmail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/email-accounts")
async def debug_email_accounts(current_user: User = Depends(get_current_user)):
    """Debug endpoint to test email accounts functionality"""
    try:
        return {
            "status": "success",
            "message": "Email accounts endpoints are working",
            "user_id": current_user.id,
            "endpoints_available": [
                "GET /api/v1/email-accounts",
                "POST /api/v1/email-accounts/gmail",
                "GET /api/v1/email-accounts/connect/gmail/url",
                "POST /api/v1/email-accounts/connect/gmail",
                "POST /api/v1/email-accounts/connect/gmail/code",
            ],
        }
    except Exception as e:
        return {"error": str(e)}
