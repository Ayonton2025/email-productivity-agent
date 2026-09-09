"""Canonical mailbox and message models."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from app.models.base import Base
from app.models.serialization import _to_utc_iso


class UserEmailAccount(Base):
    __tablename__ = "user_email_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # gmail, yahoo, outlook, etc
    email_account_type = Column(String, default="external", nullable=False, index=True)  # external | hosted_internal
    hosted_provider = Column(String, nullable=True)  # mailcow, postal, mailu, resend, sendgrid
    email = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)

    # IMAP/SMTP Configuration
    imap_host = Column(String, nullable=False)
    imap_port = Column(Integer, default=993)
    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, default=587)
    use_tls = Column(Boolean, default=True)

    # ENCRYPTED Credentials
    encrypted_password = Column(Text, nullable=False)  # AES-256 encrypted IMAP/SMTP password

    # OAuth Tokens (for providers like Gmail)
    access_token = Column(Text, nullable=True)  # ENCRYPTED OAuth access token
    refresh_token = Column(Text, nullable=True)  # ENCRYPTED OAuth refresh token
    token_expires_at = Column(DateTime, nullable=True)  # When access token expires

    # Gmail Push Notifications
    history_id = Column(String, nullable=True)  # Gmail history ID for incremental sync
    watch_expiration = Column(DateTime, nullable=True)  # When Gmail watch expires

    # Connection Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    last_sync = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)
    last_sync_status = Column(String, nullable=True)  # "success", "failed", etc
    sync_error = Column(Text, nullable=True)  # Last sync error message

    # Metadata
    total_emails = Column(Integer, default=0)
    unread_count = Column(Integer, default=0)
    send_limit_daily = Column(Integer, default=0)  # 0 means no explicit account-level cap
    send_count_daily = Column(Integer, default=0)
    send_count_reset_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "email_account_type": self.email_account_type,
            "hosted_provider": self.hosted_provider,
            "email": self.email,
            "display_name": self.display_name,
            "imap_host": self.imap_host,
            "imap_port": self.imap_port,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "use_tls": self.use_tls,
            "is_active": self.is_active,
            "is_primary": self.is_primary,
            "last_sync": _to_utc_iso(self.last_sync),
            "last_sync_status": self.last_sync_status,
            "sync_enabled": self.sync_enabled,
            "total_emails": self.total_emails,
            "unread_count": self.unread_count,
            "send_limit_daily": self.send_limit_daily,
            "send_count_daily": self.send_count_daily,
            "send_count_reset_at": _to_utc_iso(self.send_count_reset_at),
            "created_at": _to_utc_iso(self.created_at),
            "provider": self.provider,
            "has_oauth": bool(self.access_token),
            "watch_expiration": _to_utc_iso(self.watch_expiration),
        }


class Email(Base):
    __tablename__ = "emails"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, ForeignKey("user_email_accounts.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Email Identifiers
    message_id = Column(String, nullable=False, index=True)  # RFC822 Message-ID
    uid = Column(
        BigInteger, nullable=False
    )  # IMAP UID (unique per mailbox) - BigInteger for Gmail internalDate in milliseconds

    # Core Email Data
    sender = Column(String, nullable=False, index=True)
    recipients = Column(JSON, default=list)  # List of "to" addresses
    cc = Column(JSON, default=list)
    bcc = Column(JSON, default=list)
    subject = Column(String, nullable=True)

    # Email Content
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    attachments = Column(JSON, default=list)  # List of attachment metadata

    # Email Metadata
    received_at = Column(DateTime, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    folder = Column(String, default="INBOX", index=True)  # INBOX, Sent, Drafts, etc

    # Email Flags
    is_read = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    is_draft = Column(Boolean, default=False)
    is_spam = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    # Raw Email
    raw_mime = Column(Text, nullable=True)  # Full RFC822 email for reconstruction

    # AI Processing
    ai_category = Column(String, nullable=True)  # urgent, needs_reply, task, fyi, spam
    ai_summary = Column(Text, nullable=True)
    priority = Column(String, default="medium")  # For compatibility
    action_items = Column(JSON, default=list)
    sentiment = Column(String, nullable=True)
    future_priority_score = Column(Float, nullable=True)
    processing_status = Column(String, default="pending")

    # Threading
    thread_id = Column(String, nullable=True, index=True)  # For conversation grouping
    in_reply_to = Column(String, nullable=True)
    references = Column(JSON, default=list)

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    synced_at = Column(DateTime, default=datetime.utcnow)  # When fetched from provider

    # Follow-up automation fields (Phase 1)
    last_sent_at = Column(DateTime, nullable=True, index=True)
    replied_at = Column(DateTime, nullable=True, index=True)
    follow_up_stage = Column(Integer, default=0)
    follow_up_scheduled_at = Column(DateTime, nullable=True, index=True)
    follow_up_enabled = Column(Boolean, default=False, index=True)

    __table_args__ = (
        Index("idx_account_folder", "account_id", "folder"),
        Index("idx_user_timestamp", "user_id", "received_at"),
        Index("idx_message_id", "message_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "message_id": self.message_id,
            "sender": self.sender,
            "recipients": self.recipients,
            "cc": self.cc,
            "bcc": self.bcc,
            "subject": self.subject,
            # Primary content fields
            "body_text": self.body_text,
            "body_html": self.body_html,
            "attachments": self.attachments,
            "received_at": _to_utc_iso(self.received_at),
            "sent_at": _to_utc_iso(self.sent_at),
            "folder": self.folder,
            "is_read": self.is_read,
            "is_flagged": self.is_flagged,
            "is_draft": self.is_draft,
            "is_spam": self.is_spam,
            "is_archived": self.is_archived,
            "ai_category": self.ai_category,
            "ai_summary": self.ai_summary,
            "priority": self.priority,
            "action_items": self.action_items,
            "sentiment": self.sentiment,
            "future_priority_score": self.future_priority_score,
            "thread_id": self.thread_id,
            "in_reply_to": self.in_reply_to,
            "last_sent_at": _to_utc_iso(self.last_sent_at),
            "replied_at": _to_utc_iso(self.replied_at),
            "follow_up_stage": self.follow_up_stage,
            "follow_up_scheduled_at": _to_utc_iso(self.follow_up_scheduled_at),
            "follow_up_enabled": self.follow_up_enabled,
            "created_at": _to_utc_iso(self.created_at),
            # Compatibility fields (some frontend components still expect these)
            "timestamp": _to_utc_iso(self.received_at),
            "body": self.body_text or self.body_html or "",
            "category": self.ai_category,
            "summary": self.ai_summary,
            "is_starred": self.is_flagged,
        }


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # ADDED
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    recipient = Column(String, nullable=True)
    context_email_id = Column(String, nullable=True)
    draft_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,  # ADDED
            "subject": self.subject,
            "body": self.body,
            "recipient": self.recipient,
            "context_email_id": self.context_email_id,
            "metadata": self.draft_metadata or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
