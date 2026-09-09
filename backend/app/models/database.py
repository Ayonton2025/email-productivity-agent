"""Database lifecycle and compatibility exports for canonical domain models."""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models.email_models import Email, EmailDraft, UserEmailAccount
from app.models.prompt_models import PromptTemplate
from app.models.provider_models import EmailProviderConfig, SyncHistory
from app.models.serialization import _to_utc_iso
from app.models.system_models import SystemSetting
from app.models.user_models import User

__all__ = [
    "Base",
    "User",
    "UserEmailAccount",
    "Email",
    "EmailDraft",
    "PromptTemplate",
    "EmailProviderConfig",
    "SyncHistory",
    "SystemSetting",
    "engine",
    "AsyncSessionLocal",
    "init_db",
    "create_default_prompts",
    "get_db",
    "_to_utc_iso",
]
logger = logging.getLogger(__name__)


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
    from app.models import register_models

    register_models()
    try:
        # Ensure all model modules are imported so their mappings are registered
        # with SQLAlchemy's declarative base before running create_all.

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
                    logger.info(f"⚠️  [init_db] Could not drop index (may not exist): {idx_err}")

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
                logger.info("✅ LLM provider configs table ensured")
            except Exception as llm_err:
                logger.info(f"⚠️  [init_db] LLM provider table creation note: {llm_err}")

            # Create index for LLM provider lookups
            try:
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_llm_provider_priority_enabled ON llm_provider_configs (is_enabled, priority)"
                    )
                )
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
                    logger.info(f"⚠️  [init_db] Phase 1 migration warning for '{stmt}': {alter_err}")

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
                    logger.info(f"⚠️  [init_db] Hosted email migration warning for '{stmt}': {alter_err}")

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
                    logger.info(f"⚠️  [init_db] Billing migration warning for '{stmt}': {alter_err}")

        # Create default system prompts after tables are created
        await create_default_prompts()
    except Exception as e:
        # If there are index conflicts (e.g., duplicate index names), log and continue
        # This can happen if the database schema was partially created before
        import traceback

        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            logger.error(f"⚠️ [init_db] Database initialization warning: {error_msg}")
            logger.info("⚠️ [init_db] This is usually safe to ignore if tables already exist.")
            logger.error("⚠️ [init_db] If you see persistent errors, delete backend/local.db and restart.")
        else:
            # Re-raise other errors
            logger.error(f"❌ [init_db] Database initialization failed: {error_msg}")
            logger.info(f"❌ [init_db] Stack trace: {traceback.format_exc()}")
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
                "is_active": True,
            },
            {
                "name": "Action Item Extractor",
                "description": "Extract specific tasks and action items from emails",
                "template": "Extract all actionable tasks, to-do items, or requests from this email. For each item, identify:\n- The specific task to be done\n- Any mentioned deadlines or due dates\n- The priority level (high, medium, low)\n- The person responsible (if mentioned)\n\nFormat your response as a JSON array of objects with these fields: task, deadline, priority, assigned_to.\n\nIf no clear action items are found, return an empty array.\n\nEmail Content:\n{email_content}\n\nRespond with valid JSON only.",
                "category": "action_extraction",
                "is_system": True,
                "is_active": True,
            },
            {
                "name": "Professional Reply Drafter",
                "description": "Draft professional email responses",
                "template": "Draft a professional email reply based on the original email. Follow these guidelines:\n\n1. Be polite and professional\n2. Address all points mentioned in the original email\n3. Maintain appropriate tone based on the sender's relationship\n4. If it's a meeting request, ask for an agenda\n5. If it's a task request, provide a realistic timeline\n6. Keep it concise but comprehensive\n7. Use proper email formatting\n\nOriginal Email:\nFrom: {sender}\nSubject: {subject}\nBody: {body}\n\nDraft your response as if you are the recipient. Include a proper subject line (usually 'Re: [original subject]') and salutation.",
                "category": "reply_draft",
                "is_system": True,
                "is_active": True,
            },
            {
                "name": "Concise Summarizer",
                "description": "Create brief, informative email summaries",
                "template": "Provide a concise summary of this email in 2-3 sentences. Focus on:\n- The main purpose or key message\n- Any specific requests or action items\n- Important deadlines or dates\n- Key people or stakeholders mentioned\n\nKeep it brief but informative. Avoid unnecessary details.\n\nEmail Content:\n{email_content}\n\nProvide only the summary, no additional commentary.",
                "category": "summary",
                "is_system": True,
                "is_active": True,
            },
        ]

        for prompt_data in default_prompts:
            prompt = PromptTemplate(**prompt_data)
            session.add(prompt)

        await session.commit()
        logger.info("✅ Default system prompts created successfully")


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
    logger.info("Creating database tables...")
    asyncio.run(init_db())
    logger.info("Database tables created successfully.")
