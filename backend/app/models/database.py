from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey, Index
from datetime import datetime, timedelta  # ADDED timedelta import
import uuid
import asyncio
import jwt
from app.core.config import settings
from app.core.security import get_password_hash, verify_password

# Base declarative class
Base = declarative_base()


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
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
        }


class UserEmailAccount(Base):
    __tablename__ = "user_email_accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    provider = Column(String, nullable=False)  # gmail, outlook
    email = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    last_sync = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_primary": self.is_primary,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "sync_enabled": self.sync_enabled,
            "created_at": self.created_at.isoformat(),
        }


# ==========================
# EMAIL MODELS (Updated with user_id)
# ==========================
class Email(Base):
    __tablename__ = "emails"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)  # ADDED
    sender = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    category = Column(String, default="Uncategorized")
    priority = Column(String, default="medium")
    is_read = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    email_metadata = Column(JSON, default=dict)
    action_items = Column(JSON, default=list)
    summary = Column(Text, nullable=True)
    sentiment = Column(String, nullable=True)
    processing_status = Column(String, default="pending")
    source_provider = Column(String, nullable=True)  # gmail, outlook, etc.
    source_email_id = Column(String, nullable=True)  # Original email ID from provider
    
    # Add indexes for better performance
    __table_args__ = (
        Index('ix_emails_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_emails_user_category', 'user_id', 'category'),
        Index('ix_emails_user_priority', 'user_id', 'priority'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,  # ADDED
            "sender": self.sender,
            "subject": self.subject,
            "body": self.body,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "category": self.category,
            "priority": self.priority,
            "is_read": self.is_read,
            "is_archived": self.is_archived,
            "is_starred": self.is_starred,
            "metadata": self.email_metadata or {},
            "action_items": self.action_items or [],
            "summary": self.summary,
            "sentiment": self.sentiment,
            "processing_status": self.processing_status,
            "source_provider": self.source_provider,
            "source_email_id": self.source_email_id
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create default system prompts after tables are created
    await create_default_prompts()


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
