"""
Gmail INBOX sync service (OAuth-based).

This bridges Gmail OAuth tokens (stored in EmailProviderConfig) with the
existing Email Accounts + Emails tables used by the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.security import decrypt_credential
from app.models.database import Email, EmailProviderConfig, UserEmailAccount, User
from app.services.email_ai_processing_service import process_emails_ai
from app.services.auto_reply_service import AutoReplyService
from app.services.email_attachment_integration import email_attachment_integration

try:
    from app.tasks.document_analysis_task import task_handler
    HAS_DOCUMENT_ANALYSIS = True
except ImportError:
    HAS_DOCUMENT_ANALYSIS = False

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def _dt_from_internal_date_ms(ms: Optional[str]) -> datetime:
    try:
        if not ms:
            return datetime.now(timezone.utc)
        return datetime.fromtimestamp(int(ms) / 1000.0, tz=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _header(headers: List[Dict[str, str]], name: str, default: str = "") -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", default)
    return default


def _extract_body(payload: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (body_text, body_html). Prefer plain text; fallback to html/snippet.
    """

    def walk_parts(part: Dict[str, Any]) -> List[Dict[str, Any]]:
        parts = []
        if "parts" in part and isinstance(part["parts"], list):
            for p in part["parts"]:
                parts.extend(walk_parts(p))
        parts.append(part)
        return parts

    body_text = ""
    body_html = ""

    for part in walk_parts(payload):
        mime = part.get("mimeType")
        body = part.get("body") or {}
        data = body.get("data")
        if not data:
            continue

        # Gmail uses URL-safe base64 without padding sometimes
        import base64

        try:
            decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        except Exception:
            continue

        if mime == "text/plain" and not body_text:
            body_text = decoded
        elif mime == "text/html" and not body_html:
            body_html = decoded

    return body_text, body_html


def _extract_attachments(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract attachment metadata from Gmail payload.
    """
    attachments: List[Dict[str, Any]] = []

    def walk_parts(part: Dict[str, Any]) -> List[Dict[str, Any]]:
        parts = []
        if "parts" in part and isinstance(part["parts"], list):
            for p in part["parts"]:
                parts.extend(walk_parts(p))
        parts.append(part)
        return parts

    for part in walk_parts(payload):
        filename = part.get("filename")
        body = part.get("body") or {}
        attachment_id = body.get("attachmentId")
        size = body.get("size", 0)
        mime_type = part.get("mimeType", "")
        if filename and attachment_id:
            attachments.append(
                {
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": size,
                    "attachment_id": attachment_id,
                }
            )

    return attachments


def _map_ai_category(label_ids: List[str]) -> Optional[str]:
    labels = set(label_ids or [])
    if "SPAM" in labels:
        return "Spam"
    if "CATEGORY_PROMOTIONS" in labels or "CATEGORY_UPDATES" in labels or "CATEGORY_FORUMS" in labels:
        return "Newsletter"
    if "CATEGORY_SOCIAL" in labels:
        return "Personal"
    if "IMPORTANT" in labels:
        return "Important"
    return "Uncategorized"


async def get_gmail_provider_config(db: AsyncSession, user_id: str) -> Optional[EmailProviderConfig]:
    stmt = select(EmailProviderConfig).where(
        and_(
            EmailProviderConfig.user_id == user_id,
            EmailProviderConfig.provider == "gmail",
            EmailProviderConfig.is_active == True,
        )
    )
    result = await db.execute(
        stmt.order_by(EmailProviderConfig.updated_at.desc(), EmailProviderConfig.created_at.desc())
    )
    rows = list(result.scalars().all())
    if not rows:
        return None
    if len(rows) > 1:
        # Keep sync path resilient if duplicate active rows exist.
        return rows[0]
    return rows[0]


def _build_credentials_from_config(config: EmailProviderConfig) -> Credentials:
    cfg = config.config_data or {}

    access_token_enc = cfg.get("access_token_encrypted") or cfg.get("access_token")
    refresh_token_enc = cfg.get("refresh_token_encrypted") or cfg.get("refresh_token")

    access_token = decrypt_credential(access_token_enc) if access_token_enc else None
    refresh_token = decrypt_credential(refresh_token_enc) if refresh_token_enc else None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=cfg.get("scopes") or GMAIL_SCOPES,
    )

    # Refresh if needed (requires refresh_token + client credentials)
    try:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    except Exception:
        # We'll still try with whatever token we have; caller will see API error if invalid.
        pass

    return creds


async def sync_gmail_inbox(
    db: AsyncSession,
    account: UserEmailAccount,
    max_results: int = 50,
) -> Tuple[int, str]:
    """
    Sync Gmail INBOX via Gmail API into Email table.
    Returns: (emails_synced, status_message)
    """
    provider_cfg = await get_gmail_provider_config(db, account.user_id)
    if not provider_cfg:
        return (0, "❌ Gmail not linked for this user (missing provider config)")

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return (0, "❌ Gmail OAuth not configured on backend (missing client id/secret)")

    creds = _build_credentials_from_config(provider_cfg)
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)

    # Only INBOX. We intentionally do not fetch "ALL" to avoid pulling everything at once.
    results = (
        gmail.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=max_results)
        .execute()
    )
    messages = results.get("messages", []) or []

    emails_synced = 0
    new_email_ids: List[str] = []

    user_plan = "free"
    try:
        user_result = await db.execute(select(User).where(User.id == account.user_id))
        user_row = user_result.scalars().first()
        if user_row:
            if getattr(user_row, "subscription_status", "free") == "active":
                user_plan = getattr(user_row, "plan", "pro") or "pro"
            elif (getattr(user_row, "plan", "") or "").lower() in {"pro", "plus", "professional", "enterprise"}:
                user_plan = user_row.plan
    except Exception:
        pass

    for m in messages:
        msg_id = m.get("id")
        if not msg_id:
            continue

        msg = (
            gmail.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )

        payload = msg.get("payload") or {}
        headers = payload.get("headers") or []
        label_ids = msg.get("labelIds") or []

        message_id = _header(headers, "Message-ID", default=msg_id).strip("<>")
        sender = _header(headers, "From", default="").strip() or "Unknown Sender"
        subject = _header(headers, "Subject", default="(no subject)")
        to_hdr = _header(headers, "To", default="")

        body_text, body_html = _extract_body(payload)
        attachments = _extract_attachments(payload)

        received_at = _dt_from_internal_date_ms(msg.get("internalDate"))
        is_read = "UNREAD" not in set(label_ids)
        is_spam = "SPAM" in set(label_ids)

        # De-dupe by provider message-id per account
        stmt = select(Email).where(
            and_(Email.account_id == account.id, Email.message_id == message_id)
        )
        existing = await db.execute(stmt)
        if existing.scalars().first():
            continue

        email_row = Email(
            account_id=account.id,
            user_id=account.user_id,
            message_id=message_id,
            uid=int(msg.get("internalDate") or 0),
            sender=sender,
            recipients=[to_hdr] if to_hdr else [],
            cc=[],
            bcc=[],
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            received_at=received_at.replace(tzinfo=None),
            sent_at=None,
            folder="INBOX",
            is_read=is_read,
            is_flagged=False,
            is_draft=False,
            is_spam=is_spam,
            is_archived=False,
            raw_mime=None,
            ai_category=_map_ai_category(label_ids),
            ai_summary=None,
            processing_status="pending",
            thread_id=msg.get("threadId"),
            in_reply_to=None,
            references=[],
        )

        db.add(email_row)
        await db.flush()
        emails_synced += 1
        # Track for AI processing after commit
        new_email_ids.append(email_row.id)

        # Extract and store binary attachment files
        if attachments:
            try:
                await email_attachment_integration.process_gmail_attachments(
                    service=gmail,
                    message_id=msg_id,
                    email_id=email_row.id,
                    user_id=account.user_id,
                    attachments_metadata=attachments,
                    db=db,
                )
            except Exception:
                # Do not fail sync because attachment extraction failed for one message
                pass

    # Update account stats
    account.last_sync = datetime.utcnow()
    account.last_sync_status = "success"
    account.sync_error = None
    account.total_emails = (account.total_emails or 0) + emails_synced
    # unread_count is approximate; better computed later if needed.

    provider_cfg.last_sync = datetime.utcnow()

    await db.commit()

    # Queue attachment analysis after attachments are committed
    if HAS_DOCUMENT_ANALYSIS:
        for eid in new_email_ids:
            try:
                await task_handler.analyze_email_attachments(
                    email_id=eid,
                    user_id=account.user_id,
                    user_plan=user_plan or "free",
                )
            except Exception:
                continue

    # AI processing (best-effort)
    try:
        await process_emails_ai(db, new_email_ids)
    except Exception:
        pass

    # Auto-reply (best-effort): after AI category/priority, run rules per new email
    try:
        ar = AutoReplyService(db)
        for eid in new_email_ids:
            res = await db.execute(select(Email).where(Email.id == eid))
            row = res.scalar_one_or_none()
            if not row:
                continue
            d = row.to_dict()
            d["references"] = getattr(row, "references", None) or []
            await ar.process_email_for_auto_reply(
                d, account.user_id,
                account_id=str(account.id),
                account_provider=account.provider or "gmail",
            )
    except Exception:
        pass

    return (emails_synced, f"✅ Synced {emails_synced} Gmail INBOX emails")
