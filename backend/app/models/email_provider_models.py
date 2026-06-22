from sqlalchemy import Column, String, Text, JSON, Boolean, DateTime, Integer, BigInteger, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Email(Base):
    """Synced email from IMAP mailbox"""
    __tablename__ = "emails"
    __table_args__ = (
        Index("idx_user_account", "account_id"),
        Index("idx_user_folder", "account_id", "folder"),
        Index("idx_received_date", "received_at"),
        Index("idx_message_id", "message_id"),
    )
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, nullable=False, index=True)  # UserEmailAccount ID
    user_id = Column(String, nullable=False, index=True)  # User ID for quick filtering
    
    # Email Identifiers
    message_id = Column(String, nullable=False, index=True)  # RFC822 Message-ID
    uid = Column(BigInteger, nullable=False)  # IMAP UID (unique per mailbox) - BigInteger for Gmail internalDate in milliseconds
    
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
    
    # Raw Email
    raw_mime = Column(Text, nullable=True)  # Full RFC822 email for reconstruction
    
    # AI Processing
    ai_category = Column(String, nullable=True)  # urgent, needs_reply, task, fyi, spam
    ai_summary = Column(Text, nullable=True)
    ai_embeddings = Column(JSON, nullable=True)  # Vector embeddings for search
    
    # Threading
    thread_id = Column(String, nullable=True, index=True)  # For conversation grouping
    in_reply_to = Column(String, nullable=True)
    references = Column(JSON, default=list)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    synced_at = Column(DateTime, default=datetime.utcnow)  # When fetched from provider
    
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
            "body_text": self.body_text,
            "body_html": self.body_html,
            "attachments": self.attachments,
            "received_at": self.received_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "folder": self.folder,
            "is_read": self.is_read,
            "is_flagged": self.is_flagged,
            "is_draft": self.is_draft,
            "is_spam": self.is_spam,
            "ai_category": self.ai_category,
            "ai_summary": self.ai_summary,
            "thread_id": self.thread_id,
            "in_reply_to": self.in_reply_to,
            "created_at": self.created_at.isoformat(),
        }

class SyncHistory(Base):
    __tablename__ = "sync_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, nullable=False, index=True)  # UserEmailAccount ID
    sync_type = Column(String, nullable=False)  # full, incremental
    emails_processed = Column(Integer, default=0)
    status = Column(String, default="completed")  # completed, failed, partial
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "sync_type": self.sync_type,
            "emails_processed": self.emails_processed,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class EmailProviderConfig(Base):
    __tablename__ = "email_provider_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False)  # gmail, outlook
    user_id = Column(String, nullable=False)
    config_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }