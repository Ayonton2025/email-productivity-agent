"""
Email Account Management Endpoints

Handles connecting email accounts via IMAP/SMTP (no OAuth required)
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
import logging

from app.models.database import get_db, UserEmailAccount, Email
from app.models.document_models import EmailAttachment
from app.models.user_models import User
from app.core.config import settings
from app.core.security import encrypt_credential, decrypt_credential, get_current_user
from app.services.imap_service import imap_service
from app.services.smtp_service import smtp_service
from app.models.database import EmailProviderConfig
from app.services.email_provider_service import EmailProviderService
from app.services.gmail_sync_service import sync_gmail_inbox
from app.api.schemas import EmailResponse, BulkFlagRequest, BulkMarkReadRequest, BulkCategorizeRequest

logger = logging.getLogger(__name__)

# ============== REQUEST MODELS ==============

class ConnectEmailAccountRequest(BaseModel):
    """Connect email account with IMAP/SMTP credentials"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, max_length=500, description="IMAP/SMTP password or app-specific password")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name for account")
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
            raise HTTPException(status_code=500, detail="Google OAuth not configured (missing client id)")

        logger.info(f"Generating Gmail auth URL for user {current_user.id if current_user else 'unknown'}")
        
        # Use the helper that requests Gmail scopes + offline access.
        provider = EmailProviderService()
        auth_url = provider.get_gmail_auth_url(settings.GOOGLE_CLIENT_ID, redirect_uri)
        logger.info(f"Successfully generated Gmail auth URL: {auth_url[:50]}...")
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
            raise HTTPException(status_code=500, detail="Google OAuth not configured (missing client id)")

        logger.info("Generating Gmail auth URL (public endpoint)")
        
        # Use the helper that requests Gmail scopes + offline access.
        provider = EmailProviderService()
        auth_url = provider.get_gmail_auth_url(settings.GOOGLE_CLIENT_ID, redirect_uri)
        logger.info(f"Successfully generated Gmail auth URL: {auth_url[:50]}...")
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
        raise HTTPException(status_code=500, detail="Google OAuth not configured (missing client id/secret)")

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
        raise HTTPException(status_code=400, detail=f"Failed to exchange OAuth code for tokens: {str(e)}")

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
    res_any = await db.execute(select(UserEmailAccount).where(UserEmailAccount.user_id == current_user.id))
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
                account.token_expires_at = datetime.fromisoformat(token_expiry_str.replace('Z', '+00:00'))
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

@router.post("/test-connection")
async def test_connection(
    request: TestConnectionRequest,
    current_user: User = Depends(get_current_user)
):
    """Test IMAP/SMTP connection without saving credentials"""
    try:
        # Extract domain from email
        domain = request.email.split('@')[1].lower()
        
        # Get provider config
        provider_config = settings.get_provider_config(domain)
        if not provider_config:
            return {
                "success": False,
                "message": f"❌ Email provider not supported: {domain}",
                "provider": None
            }
        
        # Create temporary account object for testing
        temp_account = UserEmailAccount(
            user_id=current_user.id,
            email=request.email,
            provider=provider_config['name'].lower(),
            imap_host=provider_config['imap_host'],
            imap_port=provider_config['imap_port'],
            smtp_host=provider_config['smtp_host'],
            smtp_port=provider_config['smtp_port'],
            use_tls=provider_config['use_tls'],
            encrypted_password=encrypt_credential(request.password)
        )
        
        # Test IMAP connection
        success, message = await imap_service.test_connection(temp_account)
        
        if success:
            return {
                "success": True,
                "message": message,
                "provider": provider_config['name'],
                "provider_key": provider_config['name'].lower(),
                "requires_app_password": provider_config.get('requires_app_password', False)
            }
        else:
            return {
                "success": False,
                "message": message,
                "provider": provider_config['name'],
                "requires_app_password": provider_config.get('requires_app_password', False)
            }
    
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return {
            "success": False,
            "message": f"❌ Connection test failed: {str(e)}"
        }

@router.post("/connect")
async def connect_email_account(
    request: ConnectEmailAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect new email account via IMAP/SMTP"""
    try:
        # Extract domain
        domain = request.email.split('@')[1].lower()
        
        # Get provider config
        if request.auto_detect_provider:
            provider_config = settings.get_provider_config(domain)
            if not provider_config:
                raise HTTPException(
                    status_code=400,
                    detail=f"Email provider not supported: {domain}"
                )
            provider_name = provider_config['name'].lower()
            imap_host = provider_config['imap_host']
            imap_port = provider_config['imap_port']
            smtp_host = provider_config['smtp_host']
            smtp_port = provider_config['smtp_port']
            use_tls = provider_config['use_tls']
        else:
            # Manual provider config would go here
            raise HTTPException(status_code=400, detail="Manual provider config not yet supported")
        
        # Check if account already exists
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.user_id == current_user.id,
                UserEmailAccount.email == request.email
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
            sync_enabled=True
        )
        
        db.add(account)
        await db.commit()
        await db.refresh(account)
        
        logger.info(f"✅ Email account connected: {request.email}")
        
        return {
            "success": True,
            "message": f"✅ Email account connected: {request.email}",
            "account": account.to_dict()
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


@router.get("/list")
async def list_email_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all connected email accounts"""
    try:
        stmt = select(UserEmailAccount).where(UserEmailAccount.user_id == current_user.id)
        result = await db.execute(stmt)
        accounts = result.scalars().all()
        
        return {
            "success": True,
            "accounts": [acc.to_dict() for acc in accounts],
            "count": len(accounts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_user_email_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's connected email accounts"""
    try:
        stmt = select(UserEmailAccount).where(
            UserEmailAccount.user_id == current_user.id
        ).order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc())
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
    db: AsyncSession = Depends(get_db)
):
    """Disconnect email account"""
    try:
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
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
    db: AsyncSession = Depends(get_db)
):
    """Sync emails from account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        
        if not account:
            logger.error(f"Account {account_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Account not found")

        limit = request.limit if request else 100
        
        logger.info(f"Starting sync for account {account.email} ({account.provider}), user {current_user.id}")

        # Gmail OAuth-based sync
        if account.provider == "gmail":
            emails_synced, status = await sync_gmail_inbox(db=db, account=account, max_results=limit)
        else:
            # IMAP-based sync
            emails_synced, status = await imap_service.sync_inbox(
                account,
                db,
                limit=limit
            )
        
        logger.info(f"Sync completed: {emails_synced} emails synced from {account.email}")
        
        return {
            "success": True,
            "message": status,
            "emails_synced": emails_synced,
            "account": account.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error for account {account_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{account_id}/inbox")
async def get_inbox(
    account_id: str,
    page: int = 0,
    per_page: int = 50,
    sync_on_load: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get inbox emails for account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Optional sync path: disabled by default so inbox rendering stays fast/reliable.
        if sync_on_load and account.provider == "gmail":
            should_sync = False
            if not account.last_sync:
                should_sync = True
            else:
                elapsed = (datetime.utcnow() - account.last_sync).total_seconds()
                should_sync = elapsed >= 60
            if should_sync:
                try:
                    await sync_gmail_inbox(db=db, account=account, max_results=max(per_page, 50))
                except Exception as e:
                    logger.warning(f"Auto-sync Gmail on inbox load failed: {e}")
        
        # Get emails
        stmt = select(Email).where(
            and_(
                Email.account_id == account_id,
                Email.folder == "INBOX"
            )
        ).order_by(Email.received_at.desc()).offset(page * per_page).limit(per_page)
        
        result = await db.execute(stmt)
        emails = result.scalars().all()

        # Load attachment counts from normalized attachment table
        attachment_counts = {}
        if emails:
            email_ids = [e.id for e in emails]
            stmt_att = select(EmailAttachment).where(EmailAttachment.email_id.in_(email_ids))
            result_att = await db.execute(stmt_att)
            attachment_rows = result_att.scalars().all()
            for att in attachment_rows:
                attachment_counts[att.email_id] = attachment_counts.get(att.email_id, 0) + 1
        
        # Get total count without loading full rows
        stmt_count = select(func.count()).select_from(Email).where(
            and_(
                Email.account_id == account_id,
                Email.folder == "INBOX"
            )
        )
        result_count = await db.execute(stmt_count)
        total = int(result_count.scalar_one() or 0)
        
        emails_data = []
        for email in emails:
            email_data = email.to_dict()
            normalized_count = attachment_counts.get(email.id, 0)
            legacy_count = len(email_data.get("attachments") or [])
            email_data["attachment_count"] = max(normalized_count, legacy_count)
            email_data["has_attachments"] = email_data["attachment_count"] > 0
            emails_data.append(email_data)

        return {
            "success": True,
            "emails": emails_data,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/email/{email_id}")
async def get_email_detail(
    account_id: str,
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full email details"""
    try:
        # Verify account ownership
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Get email
        stmt = select(Email).where(
            and_(
                Email.id == email_id,
                Email.account_id == account_id
            )
        )
        result = await db.execute(stmt)
        email = result.scalar_one_or_none()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Mark as read
        email.is_read = True
        await db.commit()
        
        # Include normalized attachment count for UI display
        stmt_att = select(EmailAttachment).where(EmailAttachment.email_id == email.id)
        result_att = await db.execute(stmt_att)
        attachment_rows = result_att.scalars().all()

        email_data = email.to_dict()
        normalized_count = len(attachment_rows)
        legacy_count = len(email_data.get("attachments") or [])
        email_data["attachment_count"] = max(normalized_count, legacy_count)
        email_data["has_attachments"] = email_data["attachment_count"] > 0

        return {
            "success": True,
            "email": email_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== SEND EMAIL ENDPOINTS ==============

@router.post("/{account_id}/send")
async def send_email(
    account_id: str,
    request: SendEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send email from account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # OAuth Gmail accounts should send via Gmail API (thread-aware).
        is_oauth_gmail = account.provider == "gmail" and bool(account.access_token)
        if is_oauth_gmail:
            from app.services.gmail_send_service import send_via_gmail_api
            await send_via_gmail_api(
                db=db,
                user_id=current_user.id,
                to=str(request.to),
                subject=request.subject,
                body=request.body_text,
                thread_id=request.thread_id,
                in_reply_to=request.in_reply_to,
                references=request.references or [],
            )
            return {
                "success": True,
                "message": "✅ Email sent successfully via Gmail API"
            }

        # Non-OAuth accounts send via SMTP.
        success, message = await smtp_service.send_email(
            account,
            db,
            to=request.to,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            cc=request.cc,
            bcc=request.bcc,
            in_reply_to=request.in_reply_to,
            references=request.references,
        )
        
        if success:
            return {
                "success": True,
                "message": message
            }
        else:
            raise HTTPException(status_code=500, detail=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send error: {e}")
        raise HTTPException(status_code=500, detail=f"Send failed: {str(e)}")


@router.get("/{account_id}/folders")
async def get_folders(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of folders for account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        folders = await imap_service.get_folder_list(account)
        
        return {
            "success": True,
            "folders": folders
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
