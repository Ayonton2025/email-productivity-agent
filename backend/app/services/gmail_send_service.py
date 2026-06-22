"""
Send email via Gmail API (OAuth).

Used for auto-reply auto-send when rule.auto_send is True.
Reuses provider config and credentials from gmail_sync_service.
"""

from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.gmail_sync_service import (
    _build_credentials_from_config,
    get_gmail_provider_config,
)
from app.core.config import settings
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


async def send_via_gmail_api(
    db: AsyncSession,
    user_id: str,
    to: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[List[str]] = None,
) -> None:
    """
    Send an email via Gmail API for the given user.
    Raises on failure.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("Gmail OAuth not configured")

    provider_cfg = await get_gmail_provider_config(db, user_id)
    if not provider_cfg:
        raise ValueError("Gmail not linked for this user")

    creds = _build_credentials_from_config(provider_cfg)
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = " ".join(references)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8").rstrip("=")
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    gmail.users().messages().send(userId="me", body=payload).execute()
    logger.info("Gmail API send OK: to=%s subject=%s", to, subject[:50])
