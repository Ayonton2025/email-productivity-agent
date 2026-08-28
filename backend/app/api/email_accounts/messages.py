"""
Email Account Management Endpoints

Handles connecting email accounts via IMAP/SMTP (no OAuth required)
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, UserEmailAccount, get_db
from app.models.document_models import EmailAttachment
from app.models.user_models import User
from app.services.gmail_sync_service import sync_gmail_inbox
from app.services.imap_service import imap_service
from app.services.smtp_service import smtp_service

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


@router.get("/{account_id}/inbox")
async def get_inbox(
    account_id: str,
    page: int = 0,
    per_page: int = 50,
    sync_on_load: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get inbox emails for account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(UserEmailAccount.id == account_id, UserEmailAccount.user_id == current_user.id)
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
        stmt = (
            select(Email)
            .where(and_(Email.account_id == account_id, Email.folder == "INBOX"))
            .order_by(Email.received_at.desc())
            .offset(page * per_page)
            .limit(per_page)
        )

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
        stmt_count = (
            select(func.count())
            .select_from(Email)
            .where(and_(Email.account_id == account_id, Email.folder == "INBOX"))
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
            "per_page": per_page,
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
    db: AsyncSession = Depends(get_db),
):
    """Get full email details"""
    try:
        # Verify account ownership
        stmt = select(UserEmailAccount).where(
            and_(UserEmailAccount.id == account_id, UserEmailAccount.user_id == current_user.id)
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Account not found")

        # Get email
        stmt = select(Email).where(and_(Email.id == email_id, Email.account_id == account_id))
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

        return {"success": True, "email": email_data}

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
    db: AsyncSession = Depends(get_db),
):
    """Send email from account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(UserEmailAccount.id == account_id, UserEmailAccount.user_id == current_user.id)
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
            return {"success": True, "message": "✅ Email sent successfully via Gmail API"}

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
            return {"success": True, "message": message}
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
    db: AsyncSession = Depends(get_db),
):
    """Get list of folders for account"""
    try:
        # Get account
        stmt = select(UserEmailAccount).where(
            and_(UserEmailAccount.id == account_id, UserEmailAccount.user_id == current_user.id)
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        folders = await imap_service.get_folder_list(account)

        return {"success": True, "folders": folders}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
