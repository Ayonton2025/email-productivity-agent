"""
Email Account Management Endpoints

Handles connecting email accounts via IMAP/SMTP (no OAuth required)
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import UserEmailAccount, get_db
from app.models.user_models import User
from app.services.gmail_sync_service import sync_gmail_inbox
from app.services.imap_service import imap_service

logger = logging.getLogger(__name__)

# ============== REQUEST MODELS ==============


class ConnectEmailAccountRequest(BaseModel):
    """Connect email account with IMAP/SMTP credentials"""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(
        ..., min_length=1, max_length=500, description="IMAP/SMTP password or app-specific password"
    )
    display_name: Optional[str] = Field(
        None, max_length=255, description="Display name for account"
    )
    auto_detect_provider: bool = Field(default=True, description="Auto-detect IMAP/SMTP settings")


class TestConnectionRequest(BaseModel):
    """Test email account connection"""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, max_length=500, description="Account password")


class SendEmailRequest(BaseModel):
    """Send email via account"""

    account_id: str = Field(..., description="Email account ID to send from")
    to: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, max_length=1000, description="Email subject")
    body_text: str = Field(..., max_length=100000, description="Plain text body")
    body_html: Optional[str] = Field(None, max_length=100000, description="HTML body")
    cc: Optional[List[EmailStr]] = Field(None, max_items=50, description="CC recipients")
    bcc: Optional[List[EmailStr]] = None
    in_reply_to: Optional[str] = None
    references: Optional[List[str]] = None
    thread_id: Optional[str] = None


class SyncEmailsRequest(BaseModel):
    """Sync emails from account"""

    # account_id is provided via the path parameter; do not require it in the body.
    folder: str = "INBOX"
    limit: int = 100


class GmailCodeAuthRequest(BaseModel):
    """Connect Gmail via OAuth authorization code (server-side exchange)."""

    code: str
    redirect_uri: str


class OutlookConnectRequest(BaseModel):
    """Legacy Outlook connect payload compatibility."""

    email: Optional[EmailStr] = None
    password: Optional[str] = None
    app_password: Optional[str] = None
    display_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None


# ============== ROUTER ==============

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])


# ============== GMAIL OAUTH (LINK ACCOUNT) ==============


@router.get("/list")
async def list_email_accounts(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List all connected email accounts"""
    try:
        stmt = select(UserEmailAccount).where(UserEmailAccount.user_id == current_user.id)
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        return {
            "success": True,
            "accounts": [acc.to_dict() for acc in accounts],
            "count": len(accounts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_user_email_accounts(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get user's connected email accounts"""
    try:
        stmt = (
            select(UserEmailAccount)
            .where(UserEmailAccount.user_id == current_user.id)
            .order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc())
        )
        result = await db.execute(stmt)
        accounts = result.scalars().all()
        return [account.to_dict() for account in accounts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}")
async def get_email_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Legacy compatibility route for emailAccountsApi.getAccount."""
    try:
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id,
            )
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return account.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{account_id}")
async def disconnect_email_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect email account"""
    try:
        stmt = select(UserEmailAccount).where(
            and_(UserEmailAccount.id == account_id, UserEmailAccount.user_id == current_user.id)
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # AsyncSession.delete must be awaited or row won't be removed.
        await db.delete(account)
        await db.commit()

        logger.info(f"Account {account_id} disconnected successfully for user {current_user.id}")
        return {"success": True, "message": "Account disconnected"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect account {account_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect account: {str(e)}")


# ============== EMAIL SYNC ENDPOINTS ==============


@router.post("/{account_id}/sync")
async def sync_emails(
    account_id: str,
    request: Optional[SyncEmailsRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync emails from account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(UserEmailAccount.id == account_id, UserEmailAccount.user_id == current_user.id)
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            logger.error(f"Account {account_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Account not found")

        limit = request.limit if request else 100

        logger.info(
            f"Starting sync for account {account.email} ({account.provider}), user {current_user.id}"
        )

        # Gmail OAuth-based sync
        if account.provider == "gmail":
            emails_synced, status = await sync_gmail_inbox(
                db=db, account=account, max_results=limit
            )
        else:
            # IMAP-based sync
            emails_synced, status = await imap_service.sync_inbox(account, db, limit=limit)

        logger.info(f"Sync completed: {emails_synced} emails synced from {account.email}")

        return {
            "success": True,
            "message": status,
            "emails_synced": emails_synced,
            "account": account.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error for account {account_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
