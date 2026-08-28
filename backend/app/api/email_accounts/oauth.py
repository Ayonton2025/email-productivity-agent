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
from app.models.database import EmailProviderConfig, UserEmailAccount, get_db
from app.models.user_models import User
from app.services.email_provider_service import EmailProviderService

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


@router.get("/gmail/auth-url")
async def gmail_auth_url(
    redirect_uri: str,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a Google OAuth URL for linking Gmail (requires user session).
    """
    try:
        if not settings.GOOGLE_CLIENT_ID:
            logger.error("Google OAuth not configured - missing GOOGLE_CLIENT_ID")
            raise HTTPException(
                status_code=500, detail="Google OAuth not configured (missing client id)"
            )

        logger.info(
            f"Generating Gmail auth URL for user {current_user.id if current_user else 'unknown'}"
        )

        # Use the helper that requests Gmail scopes + offline access.
        provider = EmailProviderService()
        auth_url = provider.get_gmail_auth_url(settings.GOOGLE_CLIENT_ID, redirect_uri)
        logger.info("Successfully generated Gmail authorization URL")
        return {"success": True, "auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error generating Gmail auth URL: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")


@router.get("/gmail/auth-url/public")
async def gmail_auth_url_public(redirect_uri: str):
    """
    Generate a Google OAuth URL for linking Gmail (public endpoint, no auth required).
    Use this endpoint if user is not yet logged in.
    """
    try:
        if not settings.GOOGLE_CLIENT_ID:
            logger.error("Google OAuth not configured - missing GOOGLE_CLIENT_ID")
            raise HTTPException(
                status_code=500, detail="Google OAuth not configured (missing client id)"
            )

        logger.info("Generating Gmail auth URL (public endpoint)")

        # Use the helper that requests Gmail scopes + offline access.
        provider = EmailProviderService()
        auth_url = provider.get_gmail_auth_url(settings.GOOGLE_CLIENT_ID, redirect_uri)
        logger.info("Successfully generated Gmail authorization URL")
        return {"success": True, "auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error generating Gmail auth URL: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")


@router.post("/gmail/code")
async def gmail_connect_with_code(
    request: GmailCodeAuthRequest,
    bootstrap_sync: bool = False,
    bootstrap_limit: int = 20,
    bootstrap_ai: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange OAuth code for tokens, persist them for the current user,
    and create/update a visible UserEmailAccount entry for Gmail.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500, detail="Google OAuth not configured (missing client id/secret)"
        )

    provider = EmailProviderService()

    try:
        tokens = await provider.exchange_gmail_code(
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
            request.code,
            request.redirect_uri,
        )
    except ValueError as e:
        logger.error(f"❌ Gmail OAuth code exchange failed - Invalid value: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid OAuth code or redirect URI: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Gmail OAuth code exchange failed: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to exchange OAuth code for tokens: {str(e)}"
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    # Validate token and get profile email (best-effort)
    profile_email = None
    try:
        ok = await provider.authenticate_gmail_with_token(access_token, refresh_token)
        if ok and provider.gmail_service:
            profile = provider.gmail_service.users().getProfile(userId="me").execute()
            profile_email = profile.get("emailAddress")
    except Exception as e:
        logger.warning(f"Gmail token validation/profile lookup failed: {e}")

    # Persist provider config (encrypted tokens)
    stmt = select(EmailProviderConfig).where(
        and_(
            EmailProviderConfig.user_id == current_user.id,
            EmailProviderConfig.provider == "gmail",
            EmailProviderConfig.is_active == True,
        )
    )
    result = await db.execute(
        stmt.order_by(EmailProviderConfig.updated_at.desc(), EmailProviderConfig.created_at.desc())
    )
    provider_cfgs = list(result.scalars().all())
    provider_cfg = provider_cfgs[0] if provider_cfgs else None
    if len(provider_cfgs) > 1:
        logger.warning(
            "Found %s active Gmail provider configs for user %s; keeping newest and deactivating extras",
            len(provider_cfgs),
            current_user.id,
        )
        for stale_cfg in provider_cfgs[1:]:
            stale_cfg.is_active = False

    cfg_data = {
        "email": profile_email,
        "access_token_encrypted": encrypt_credential(access_token) if access_token else None,
        "refresh_token_encrypted": encrypt_credential(refresh_token) if refresh_token else None,
        # JSON field must be serializable; store expiry as ISO string if datetime
        "token_expiry": (
            tokens.get("token_expiry").isoformat()
            if isinstance(tokens.get("token_expiry"), datetime)
            else tokens.get("token_expiry")
        ),
        "scopes": tokens.get("scopes"),
    }

    if provider_cfg:
        provider_cfg.config_data = cfg_data
        provider_cfg.last_sync = None
        provider_cfg.updated_at = datetime.utcnow()
    else:
        provider_cfg = EmailProviderConfig(
            provider="gmail",
            user_id=current_user.id,
            config_data=cfg_data,
            is_active=True,
        )
        db.add(provider_cfg)

    # Create/update a visible email account record (used by the frontend pages)
    gmail_domain_cfg = settings.get_provider_config("gmail.com") or {
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "name": "Gmail",
    }

    account_email = profile_email or f"{current_user.email}"
    stmt_acc = select(UserEmailAccount).where(
        and_(
            UserEmailAccount.user_id == current_user.id,
            UserEmailAccount.provider == "gmail",
            UserEmailAccount.email == account_email,
        )
    )
    res_acc = await db.execute(stmt_acc)
    existing_account = res_acc.scalar_one_or_none()

    # Make primary only if this is the first connected account
    res_any = await db.execute(
        select(UserEmailAccount).where(UserEmailAccount.user_id == current_user.id)
    )
    has_any_accounts = res_any.scalars().first() is not None

    if existing_account:
        existing_account.is_active = True
        existing_account.sync_enabled = True
        existing_account.display_name = existing_account.display_name or account_email
        account = existing_account
    else:
        account = UserEmailAccount(
            user_id=current_user.id,
            email=account_email,
            provider="gmail",
            display_name=account_email,
            imap_host=gmail_domain_cfg["imap_host"],
            imap_port=gmail_domain_cfg["imap_port"],
            smtp_host=gmail_domain_cfg["smtp_host"],
            smtp_port=gmail_domain_cfg["smtp_port"],
            use_tls=gmail_domain_cfg["use_tls"],
            # Placeholder; OAuth credentials are stored in EmailProviderConfig.
            encrypted_password=encrypt_credential("__OAUTH__"),
            is_primary=not has_any_accounts,
            is_active=True,
            sync_enabled=True,
        )
        db.add(account)

    # Store OAuth tokens in the account record
    account.access_token = encrypt_credential(access_token) if access_token else None
    account.refresh_token = encrypt_credential(refresh_token) if refresh_token else None
    # Convert token_expiry string to datetime object
    token_expiry_str = tokens.get("token_expiry")
    if token_expiry_str:
        if isinstance(token_expiry_str, str):
            try:
                # Parse ISO format datetime string
                account.token_expires_at = datetime.fromisoformat(
                    token_expiry_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                account.token_expires_at = None
        else:
            account.token_expires_at = token_expiry_str
    else:
        account.token_expires_at = None

    await db.commit()
    await db.refresh(account)

    # Optional bootstrap sync. Disabled by default so OAuth linking returns quickly and
    # does not time out under local-model load.
    bootstrap_synced = False
    bootstrap_synced_count = 0
    if bootstrap_sync:
        try:
            logger.info(f"🚀 Triggering bootstrap Gmail sync for account {account.id}")
            from app.services.gmail_ingestion_service import GmailIngestionService

            ingestion_service = GmailIngestionService(db)
            service = ingestion_service.build_gmail_service(access_token)

            safe_limit = max(1, min(int(bootstrap_limit or 20), 100))
            raw_emails = await ingestion_service.fetch_last_n_emails(service, n=safe_limit)
            parsed_emails = [ingestion_service.parse_gmail_message(msg) for msg in raw_emails]
            message_ids = [msg.get("id") for msg in raw_emails]
            email_ids = await ingestion_service.store_emails(
                user_id=current_user.id,
                account_id=account.id,
                parsed_emails=parsed_emails,
                gmail_service=service,
                message_ids=message_ids,
            )
            bootstrap_synced = True
            bootstrap_synced_count = len(email_ids)
            logger.info(f"✅ Bootstrap sync stored {bootstrap_synced_count} emails")

            if bootstrap_ai and email_ids:
                processed_count = await ingestion_service.process_emails_with_ai(email_ids)
                logger.info(f"✅ Bootstrap AI processing completed for {processed_count} emails")

            account.last_sync = datetime.utcnow()
            account.last_sync_status = "success"
            account.total_emails = max(account.total_emails or 0, bootstrap_synced_count)
            account.sync_error = None
            await db.commit()
        except Exception as e:
            logger.error(f"❌ Bootstrap email sync failed: {e}")
            account.last_sync_status = "failed"
            account.sync_error = str(e)
            await db.commit()

    return {
        "success": True,
        "message": (
            f"✅ Gmail linked successfully. Bootstrap synced {bootstrap_synced_count} emails."
            if bootstrap_synced
            else "✅ Gmail linked successfully. Run sync to fetch inbox emails."
        ),
        "account": account.to_dict(),
        "bootstrap_sync": {
            "enabled": bool(bootstrap_sync),
            "synced": bootstrap_synced,
            "emails_synced": bootstrap_synced_count,
            "ai_enabled": bool(bootstrap_ai),
        },
    }


# ============== CONNECTION ENDPOINTS ==============
