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

from app.core.config import settings
from app.core.security import encrypt_credential, get_current_user
from app.models.database import UserEmailAccount, get_db
from app.models.user_models import User
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


@router.post("/test-connection")
async def test_connection(
    request: TestConnectionRequest, current_user: User = Depends(get_current_user)
):
    """Test IMAP/SMTP connection without saving credentials"""
    try:
        # Extract domain from email
        domain = request.email.split("@")[1].lower()

        # Get provider config
        provider_config = settings.get_provider_config(domain)
        if not provider_config:
            return {
                "success": False,
                "message": f"❌ Email provider not supported: {domain}",
                "provider": None,
            }

        # Create temporary account object for testing
        temp_account = UserEmailAccount(
            user_id=current_user.id,
            email=request.email,
            provider=provider_config["name"].lower(),
            imap_host=provider_config["imap_host"],
            imap_port=provider_config["imap_port"],
            smtp_host=provider_config["smtp_host"],
            smtp_port=provider_config["smtp_port"],
            use_tls=provider_config["use_tls"],
            encrypted_password=encrypt_credential(request.password),
        )

        # Test IMAP connection
        success, message = await imap_service.test_connection(temp_account)

        if success:
            return {
                "success": True,
                "message": message,
                "provider": provider_config["name"],
                "provider_key": provider_config["name"].lower(),
                "requires_app_password": provider_config.get("requires_app_password", False),
            }
        else:
            return {
                "success": False,
                "message": message,
                "provider": provider_config["name"],
                "requires_app_password": provider_config.get("requires_app_password", False),
            }

    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return {"success": False, "message": f"❌ Connection test failed: {str(e)}"}


@router.post("/connect")
async def connect_email_account(
    request: ConnectEmailAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect new email account via IMAP/SMTP"""
    try:
        # Extract domain
        domain = request.email.split("@")[1].lower()

        # Get provider config
        if request.auto_detect_provider:
            provider_config = settings.get_provider_config(domain)
            if not provider_config:
                raise HTTPException(
                    status_code=400, detail=f"Email provider not supported: {domain}"
                )
            provider_name = provider_config["name"].lower()
            imap_host = provider_config["imap_host"]
            imap_port = provider_config["imap_port"]
            smtp_host = provider_config["smtp_host"]
            smtp_port = provider_config["smtp_port"]
            use_tls = provider_config["use_tls"]
        else:
            # Manual provider config would go here
            raise HTTPException(status_code=400, detail="Manual provider config not yet supported")

        # Check if account already exists
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.user_id == current_user.id, UserEmailAccount.email == request.email
            )
        )
        existing = await db.execute(stmt)
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email account already connected")

        # Encrypt password
        encrypted_password = encrypt_credential(request.password)

        # Create account record
        account = UserEmailAccount(
            user_id=current_user.id,
            email=request.email,
            provider=provider_name,
            display_name=request.display_name or request.email,
            imap_host=imap_host,
            imap_port=imap_port,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            use_tls=use_tls,
            encrypted_password=encrypted_password,
            is_primary=True,  # First account is primary
            is_active=True,
            sync_enabled=True,
        )

        db.add(account)
        await db.commit()
        await db.refresh(account)

        logger.info(f"✅ Email account connected: {request.email}")

        return {
            "success": True,
            "message": f"✅ Email account connected: {request.email}",
            "account": account.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.post("/outlook")
async def connect_outlook_legacy(
    request: OutlookConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Legacy compatibility route for frontend emailAccountsApi.connectOutlook.
    Supports:
    - Manual credentials (email + password/app_password)
    - OAuth tokens (email + access_token)
    """
    try:
        # If we have manual credentials, reuse the standard connect flow.
        manual_secret = request.app_password or request.password
        if request.email and manual_secret:
            manual_req = ConnectEmailAccountRequest(
                email=request.email,
                password=manual_secret,
                display_name=request.display_name,
                auto_detect_provider=True,
            )
            result = await connect_email_account(manual_req, current_user, db)
            account = result.get("account", {})
            account["provider"] = "outlook"
            return {**result, "account": account}

        # OAuth-style compatibility path.
        if request.email and request.access_token:
            existing_stmt = select(UserEmailAccount).where(
                and_(
                    UserEmailAccount.user_id == current_user.id,
                    UserEmailAccount.email == str(request.email),
                )
            )
            existing = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                existing.provider = "outlook"
                existing.access_token = request.access_token
                if request.refresh_token:
                    existing.refresh_token = request.refresh_token
                if request.token_expiry:
                    existing.token_expiry = request.token_expiry
                await db.commit()
                await db.refresh(existing)
                return {
                    "success": True,
                    "message": "Outlook account linked",
                    "account": existing.to_dict(),
                }

            provider_config = settings.get_provider_config("outlook.com") or {
                "imap_host": "outlook.office365.com",
                "imap_port": 993,
                "smtp_host": "smtp.office365.com",
                "smtp_port": 587,
                "use_tls": True,
            }
            account = UserEmailAccount(
                user_id=current_user.id,
                provider="outlook",
                email=str(request.email),
                display_name=request.display_name or str(request.email).split("@")[0],
                imap_host=provider_config["imap_host"],
                imap_port=provider_config["imap_port"],
                smtp_host=provider_config["smtp_host"],
                smtp_port=provider_config["smtp_port"],
                use_tls=provider_config["use_tls"],
                encrypted_password=encrypt_credential("oauth-token"),
                access_token=request.access_token,
                refresh_token=request.refresh_token,
                token_expiry=request.token_expiry,
                is_primary=False,
                is_active=True,
                sync_enabled=True,
            )
            db.add(account)
            await db.commit()
            await db.refresh(account)
            return {
                "success": True,
                "message": "Outlook account linked",
                "account": account.to_dict(),
            }

        raise HTTPException(
            status_code=400,
            detail="Provide email + password/app_password, or email + access_token",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Outlook legacy connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Outlook connection failed: {str(e)}")
