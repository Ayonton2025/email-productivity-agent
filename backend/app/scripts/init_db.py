"""One-off initialization script for DB and seed data.

Run inside Docker with:
  python -m app.scripts.init_db

This script is idempotent and safe to run multiple times. It will:
- Wait for Postgres to accept connections
- Check if a key table (users) exists and skip full init if so
- Run schema creation and seed default admin when needed
"""

import asyncio
import logging
import os
import sys

from sqlalchemy import select, text

from app.models.database import AsyncSessionLocal, User, init_db

logger = logging.getLogger(__name__)

# Configurable retry behavior via environment variables
MAX_RETRIES = int(os.environ.get("INIT_DB_MAX_RETRIES", "30"))
RETRY_DELAY = int(os.environ.get("INIT_DB_RETRY_DELAY_SEC", "2"))


async def wait_for_db():
    """Wait until the database accepts connections by attempting a simple SELECT 1."""
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
            logger.info("✅ Postgres is accepting connections")
            return True
        except Exception as e:
            attempt += 1
            logger.info(f"⏳ Waiting for Postgres (attempt {attempt}/{MAX_RETRIES}): {e}")
            await asyncio.sleep(RETRY_DELAY)
    logger.info("❌ Postgres did not become available in time")
    return False


async def is_already_initialized() -> bool:
    """Return True if expected tables already exist."""
    try:
        async with AsyncSessionLocal() as db:
            required_tables = ["users", "campaigns", "workflows", "subscriptions"]
            for table in required_tables:
                result = await db.execute(text(f"SELECT to_regclass('public.{table}')"))
                val = result.scalar_one_or_none()
                if not val:
                    logger.error(f"ℹ️ Missing table '{table}'; DB not fully initialized")
                    return False

            logger.info("ℹ️ Found required tables; assuming DB already initialized")
            return True
    except Exception as e:
        logger.error(f"⚠️ Error checking existing schema: {e}")
        return False


async def create_default_admin():
    """Create a default admin user if no users exist"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            if not users:
                admin_user = User(
                    email=os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@bylix.email"),
                    full_name="System Administrator",
                )
                admin_user.set_password(os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123"))
                admin_user.is_verified = True
                admin_user.is_active = True
                db.add(admin_user)
                await db.commit()
                logger.info("✅ Default admin user created: {}".format(admin_user.email))
            else:
                logger.info("ℹ️ Admin user already exists; skipping creation")
    except Exception as e:
        logger.info(f"⚠️ Could not create default admin: {e}")


async def main():
    logger.info("🔧 Running DB initialization script...")

    # First, wait for Postgres to be ready
    ok = await wait_for_db()
    if not ok:
        logger.info("❌ Aborting init due to unreachable DB")
        # Exit with success to avoid blocking orchestration if DB is transiently unavailable
        # Operators can inspect logs and retry later
        sys.exit(0)

    # If DB is already initialized, skip schema creation and exit cleanly
    if await is_already_initialized():
        logger.info("✅ Initialization skipped (already initialized)")
        # Still ensure default admin exists
        await create_default_admin()
        sys.exit(0)

    try:
        await init_db()
        await create_default_admin()
        logger.info("✅ Initialization script completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Initialization script failed: {e}")
        # Exit non-zero so Docker Compose knows the job failed
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
