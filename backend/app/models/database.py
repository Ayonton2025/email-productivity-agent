from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, Boolean, JSON, ForeignKey, Index, Float, text
from datetime import datetime, timedelta, timezone  # ADDED timedelta import
import uuid
import asyncio
import jwt
from app.core.config import settings
from app.core.security import get_password_hash, verify_password

# Base declarative class
Base = declarative_base()


def _to_utc_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


# ==========================
# USER MANAGEMENT MODELS
# ==========================
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    plan = Column(String, default="personal", index=True)
    subscription_status = Column(String, default="free", index=True)
    preferred_language = Column(String, default="en", index=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash)


    def generate_verification_token(self) -> str:
        token = jwt.encode(
            {"user_id": self.id, "exp": datetime.utcnow() + timedelta(days=1)},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        # Ensure token is string (jwt.encode returns bytes in some versions)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        self.verification_token = token
        return token
    
    def generate_reset_token(self) -> str:
        token = jwt.encode(
            {"user_id": self.id, "exp": datetime.utcnow() + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        # Ensure token is string
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        self.reset_token = token
        return token

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "plan": self.plan,
            "subscription_status": self.subscription_status,
            "preferred_language": self.preferred_language,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
        }


class UserEmailAccount(Base):
    __tablename__ = "user_email_accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
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


# ==========================
# EMAIL MODELS (IMAP Synced)
# ==========================
class Email(Base):
    __tablename__ = "emails"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, ForeignKey('user_email_accounts.id'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    
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
        Index('idx_account_folder', 'account_id', 'folder'),
        Index('idx_user_timestamp', 'user_id', 'received_at'),
        Index('idx_message_id', 'message_id'),
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


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=True, index=True)  # NULL for system prompts
    name = Column(String, nullable=False)
    description = Column(Text)
    template = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System prompts cannot be modified
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    prompt_metadata = Column(JSON, default=dict)
    
    # Add unique constraint for user-specific prompts
    __table_args__ = (
        Index('ix_prompts_user_name', 'user_id', 'name', unique=True),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "category": self.category,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.prompt_metadata or {}
        }


class EmailDraft(Base):
    __tablename__ = "email_drafts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)  # ADDED
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
            "updated_at": self.updated_at.isoformat()
        }


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ==========================
# EMAIL PROVIDER MODELS (Existing - keep as is)
# ==========================
class EmailProviderConfig(Base):
    __tablename__ = "email_provider_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False)  # gmail, outlook
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)  # UPDATED
    config_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "user_id": self.user_id,  # UPDATED
            "is_active": self.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class SyncHistory(Base):
    __tablename__ = "sync_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_config_id = Column(String, ForeignKey('email_provider_configs.id'), nullable=False)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)  # ADDED
    sync_type = Column(String, nullable=False)  # full, incremental
    emails_processed = Column(JSON, default=list)
    status = Column(String, default="completed")  # completed, failed, partial
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "provider_config_id": self.provider_config_id,
            "user_id": self.user_id,  # ADDED
            "sync_type": self.sync_type,
            "emails_processed": self.emails_processed,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


# ==========================
# DATABASE SETUP
# ==========================
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """
    Initialize the database: create all tables if they don't exist.
    Call this at app startup.
    """
    try:
        # Ensure all model modules are imported so their mappings are registered
        # with SQLAlchemy's declarative base before running create_all.
        import app.models.campaign_models
        import app.models.contact_models
        import app.models.user_models
        import app.models.email_provider_models
        import app.models.workflow_models
        import app.models.commitment_models
        import app.models.billing_models
        import app.models.auto_reply_models
        import app.models.agent_models
        import app.models.phase1_models
        import app.models.hosted_email_models
        import app.models.collaboration_models
        import app.models.llm_provider_models
        import app.models.meeting_models
        import app.models.security_models
        import app.models.persona_models
        import app.models.task_models
        import app.models.timeline_models
        import app.models.knowledge_models
        import app.models.offline_models

        # First, drop any conflicting indices that may exist from previous partial initialization
        async with engine.begin() as conn:
            # Drop indices that may conflict with table creation
            drop_index_statements = [
                "DROP INDEX IF EXISTS idx_user_active CASCADE",
                "DROP INDEX IF EXISTS idx_user_type CASCADE",
            ]
            for stmt in drop_index_statements:
                try:
                    await conn.execute(text(stmt))
                except Exception as idx_err:
                    print(f"⚠️  [init_db] Could not drop index (may not exist): {idx_err}")

        # Now create all tables with fresh indices
        async with engine.begin() as conn:
            # Use checkfirst=True to avoid errors if tables/indexes already exist
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))

            # Explicit table creation for LLM provider configs (sometimes missed in metadata.create_all)
            llm_provider_create_stmt = """
            CREATE TABLE IF NOT EXISTS llm_provider_configs (
                id VARCHAR NOT NULL PRIMARY KEY,
                provider VARCHAR NOT NULL UNIQUE,
                display_name VARCHAR NOT NULL,
                is_enabled BOOLEAN DEFAULT FALSE,
                priority INTEGER DEFAULT 100,
                model VARCHAR,
                endpoint VARCHAR,
                api_keys_encrypted JSON DEFAULT '[]',
                additional_headers JSON DEFAULT '{}',
                extra_config JSON DEFAULT '{}',
                max_retries INTEGER DEFAULT 2,
                backoff_seconds FLOAT DEFAULT 0.8,
                timeout_seconds INTEGER DEFAULT 30,
                is_healthy BOOLEAN DEFAULT FALSE,
                last_error TEXT,
                last_checked_at TIMESTAMP,
                updated_by VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            try:
                await conn.execute(text(llm_provider_create_stmt))
                print("✅ LLM provider configs table ensured")
            except Exception as llm_err:
                print(f"⚠️  [init_db] LLM provider table creation note: {llm_err}")

            # Create index for LLM provider lookups
            try:
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_llm_provider_priority_enabled ON llm_provider_configs (is_enabled, priority)"))
            except Exception:
                pass  # Index may already exist

            # Lightweight additive migration for Phase 1 email follow-up fields.
            # This keeps existing deployments working even without Alembic.
            phase1_alter_statements = [
                "ALTER TABLE emails ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMP",
                "ALTER TABLE emails ADD COLUMN IF NOT EXISTS replied_at TIMESTAMP",
                "ALTER TABLE emails ADD COLUMN IF NOT EXISTS follow_up_stage INTEGER DEFAULT 0",
                "ALTER TABLE emails ADD COLUMN IF NOT EXISTS follow_up_scheduled_at TIMESTAMP",
                "ALTER TABLE emails ADD COLUMN IF NOT EXISTS follow_up_enabled BOOLEAN DEFAULT FALSE",
                "CREATE INDEX IF NOT EXISTS idx_emails_follow_up_enabled ON emails (follow_up_enabled)",
                "CREATE INDEX IF NOT EXISTS idx_emails_follow_up_scheduled_at ON emails (follow_up_scheduled_at)",
                "CREATE INDEX IF NOT EXISTS idx_emails_last_sent_at ON emails (last_sent_at)",
                "CREATE INDEX IF NOT EXISTS idx_emails_replied_at ON emails (replied_at)",
            ]
            for stmt in phase1_alter_statements:
                try:
                    await conn.execute(text(stmt))
                except Exception as alter_err:
                    print(f"⚠️  [init_db] Phase 1 migration warning for '{stmt}': {alter_err}")

            hosted_alter_statements = [
                "ALTER TABLE user_email_accounts ADD COLUMN IF NOT EXISTS email_account_type VARCHAR DEFAULT 'external'",
                "ALTER TABLE user_email_accounts ADD COLUMN IF NOT EXISTS hosted_provider VARCHAR",
                "ALTER TABLE user_email_accounts ADD COLUMN IF NOT EXISTS send_limit_daily INTEGER DEFAULT 0",
                "ALTER TABLE user_email_accounts ADD COLUMN IF NOT EXISTS send_count_daily INTEGER DEFAULT 0",
                "ALTER TABLE user_email_accounts ADD COLUMN IF NOT EXISTS send_count_reset_at TIMESTAMP",
                "CREATE INDEX IF NOT EXISTS idx_user_email_accounts_type ON user_email_accounts (email_account_type)",
            ]
            for stmt in hosted_alter_statements:
                try:
                    await conn.execute(text(stmt))
                except Exception as alter_err:
                    print(f"⚠️  [init_db] Hosted email migration warning for '{stmt}': {alter_err}")

            billing_alter_statements = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR DEFAULT 'personal'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR DEFAULT 'free'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_language VARCHAR DEFAULT 'en'",
                "CREATE INDEX IF NOT EXISTS idx_users_plan ON users (plan)",
                "CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users (subscription_status)",
                "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS action VARCHAR",
                "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS tokens_used INTEGER DEFAULT 0",
                "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS credits_used INTEGER DEFAULT 0",
                "ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS timestamp TIMESTAMP DEFAULT NOW()",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS credits_total INTEGER DEFAULT 0",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS credits_used INTEGER DEFAULT 0",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS billing_cycle_start TIMESTAMP",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS billing_cycle_end TIMESTAMP",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS payment_provider VARCHAR",
                "ALTER TABLE emails ADD COLUMN IF NOT EXISTS future_priority_score DOUBLE PRECISION",
                "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS trust_score DOUBLE PRECISION DEFAULT 50.0",
                "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS stress_level DOUBLE PRECISION DEFAULT 50.0",
                "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS loyalty_score DOUBLE PRECISION DEFAULT 50.0",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS strategy_prompt TEXT",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS approval_threshold INTEGER DEFAULT 75",
            ]
            for stmt in billing_alter_statements:
                try:
                    await conn.execute(text(stmt))
                except Exception as alter_err:
                    print(f"⚠️  [init_db] Billing migration warning for '{stmt}': {alter_err}")
        
        # Create default system prompts after tables are created
        await create_default_prompts()
    except Exception as e:
        # If there are index conflicts (e.g., duplicate index names), log and continue
        # This can happen if the database schema was partially created before
        import traceback
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            print(f"⚠️ [init_db] Database initialization warning: {error_msg}")
            print("⚠️ [init_db] This is usually safe to ignore if tables already exist.")
            print("⚠️ [init_db] If you see persistent errors, delete backend/local.db and restart.")
        else:
            # Re-raise other errors
            print(f"❌ [init_db] Database initialization failed: {error_msg}")
            print(f"❌ [init_db] Stack trace: {traceback.format_exc()}")
            raise


async def create_default_prompts():
    """
    Create default system prompts for new installations.
    """
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        # Check if default prompts already exist
        result = await session.execute(select(PromptTemplate).where(PromptTemplate.is_system == True))
        existing_prompts = result.scalars().all()
        
        if existing_prompts:
            return  # Default prompts already exist
        
        default_prompts = [
            {
                "name": "Smart Categorization",
                "description": "Intelligently categorize emails into relevant categories",
                "template": "Categorize this email into exactly one of these categories: Important, Newsletter, Spam, To-Do, Personal, Work, Finance, Travel.\n\nImportant: Urgent emails requiring immediate attention, from key contacts, or containing critical information.\nNewsletter: Mass distribution emails, marketing content, updates from services.\nSpam: Unsolicited commercial emails, scams, or irrelevant content.\nTo-Do: Emails containing specific tasks, action items, or requests that need completion.\nPersonal: Non-work related emails from friends, family, or personal services.\nWork: Professional communications related to projects, meetings, or work tasks.\nFinance: Banking, invoices, payments, or financial updates.\nTravel: Flight itineraries, hotel bookings, travel plans.\n\nEmail Content:\nFrom: {sender}\nSubject: {subject}\nBody: {body}\n\nRespond with only the category name. No explanations.",
                "category": "categorization",
                "is_system": True,
                "is_active": True
            },
            {
                "name": "Action Item Extractor",
                "description": "Extract specific tasks and action items from emails",
                "template": "Extract all actionable tasks, to-do items, or requests from this email. For each item, identify:\n- The specific task to be done\n- Any mentioned deadlines or due dates\n- The priority level (high, medium, low)\n- The person responsible (if mentioned)\n\nFormat your response as a JSON array of objects with these fields: task, deadline, priority, assigned_to.\n\nIf no clear action items are found, return an empty array.\n\nEmail Content:\n{email_content}\n\nRespond with valid JSON only.",
                "category": "action_extraction",
                "is_system": True,
                "is_active": True
            },
            {
                "name": "Professional Reply Drafter",
                "description": "Draft professional email responses",
                "template": "Draft a professional email reply based on the original email. Follow these guidelines:\n\n1. Be polite and professional\n2. Address all points mentioned in the original email\n3. Maintain appropriate tone based on the sender's relationship\n4. If it's a meeting request, ask for an agenda\n5. If it's a task request, provide a realistic timeline\n6. Keep it concise but comprehensive\n7. Use proper email formatting\n\nOriginal Email:\nFrom: {sender}\nSubject: {subject}\nBody: {body}\n\nDraft your response as if you are the recipient. Include a proper subject line (usually 'Re: [original subject]') and salutation.",
                "category": "reply_draft",
                "is_system": True,
                "is_active": True
            },
            {
                "name": "Concise Summarizer",
                "description": "Create brief, informative email summaries",
                "template": "Provide a concise summary of this email in 2-3 sentences. Focus on:\n- The main purpose or key message\n- Any specific requests or action items\n- Important deadlines or dates\n- Key people or stakeholders mentioned\n\nKeep it brief but informative. Avoid unnecessary details.\n\nEmail Content:\n{email_content}\n\nProvide only the summary, no additional commentary.",
                "category": "summary",
                "is_system": True,
                "is_active": True
            }
        ]
        
        for prompt_data in default_prompts:
            prompt = PromptTemplate(**prompt_data)
            session.add(prompt)
        
        await session.commit()
        print("✅ Default system prompts created successfully")


async def get_db():
    """
    Async session generator for dependency injection.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==========================
# Optional: Quick sync helper
# ==========================
# You can run this manually to create tables without starting the server
if __name__ == "__main__":
    print("Creating database tables...")
    asyncio.run(init_db())
    print("Database tables created successfully.")
