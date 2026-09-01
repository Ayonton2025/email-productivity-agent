import os
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

load_dotenv()

from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

logger.info("🔧 Starting FastAPI application...")

from app.api.system_endpoints import RuntimeContext, create_system_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.monitoring import initialize_monitoring, register_debug_error_endpoint
from app.core.request_logging import register_request_logging
from app.core.router_loader import register_routers
from app.models.database import AsyncSessionLocal, init_db
from app.services.prompt_service import PromptService

initialize_monitoring()

secret_issues = settings.validate_critical_secrets()
if secret_issues:
    runtime_env = (os.getenv("ENV", "development") or "development").strip().lower()
    enforce_secret_validation = runtime_env in {"production", "prod"} and not settings.DEBUG
    if enforce_secret_validation:
        raise RuntimeError("Invalid security configuration in environment: " + "; ".join(secret_issues))
    logger.warning(
        "⚠️ Non-production secret validation warnings: %s",
        "; ".join(secret_issues),
    )

startup_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management: startup and shutdown hooks

    Startup: Initialize database, load models, warmup AI
    Shutdown: Close connections, flush caches, cleanup resources
    """
    logger.info("🚀 Starting Bylix Email Backend...")
    import asyncio

    async def run_startup_tasks():
        """Run DB and bootstrap tasks in background without blocking server startup."""
        from sqlalchemy import text

        skip_init = settings.SKIP_DB_INIT
        max_retries = 10
        delay = 3

        # If SKIP_DB_INIT is true, only verify DB connectivity and mark service ready
        if skip_init and not settings.ENABLE_MOCK_MODE:
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"🔎 SKIP_DB_INIT=true; verifying DB connectivity (attempt {attempt})...")
                    async with AsyncSessionLocal() as db:
                        await db.execute(text("SELECT 1"))
                        # Ensure the 'users' table exists before marking ready
                        res = await db.execute(text("SELECT to_regclass('public.users')"))
                        table_exists = res.scalar_one_or_none()
                        if table_exists:
                            globals()["startup_ready"] = True
                            logger.info("✅ DB reachable and schema present; startup marked ready (SKIP_DB_INIT)")
                            return
                        else:
                            logger.info("⚠️ DB reachable but schema missing; waiting for init_db to run")
                            # Allow retries to continue to give init_db time to run
                except Exception as e:
                    logger.error(f"⚠️ DB connectivity check failed (attempt {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, 30)
                    else:
                        logger.error("❌ Exhausted DB retries; continuing without blocking server")
                        return

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"📦 Attempting DB initialization (attempt {attempt})...")
                await init_db()
                logger.info("✅ Database initialized successfully (background)")

                # Initialize default prompts using a DB session
                try:
                    async with AsyncSessionLocal() as db:
                        prompt_service = PromptService(db)
                        await prompt_service.initialize_default_prompts()
                    logger.info("✅ Default prompts created (background)")
                except Exception as prompt_error:
                    logger.error(f"⚠️ Could not initialize default prompts: {prompt_error}")

                # Create default admin user if not exists
                await create_default_admin()
                # Mark startup as ready for readiness probes
                globals()["startup_ready"] = True
                logger.info("✅ Background startup tasks completed, service is ready")
                return
            except Exception as e:
                logger.error(f"⚠️ Background startup attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30)
                else:
                    logger.error("❌ Exhausted startup retries; continuing without blocking server")
                    return

    async def schedule_health_monitor():
        """Start LLM health monitor task (checks every 30 minutes)"""
        try:
            from app.tasks.llm_health_monitor import check_llm_provider_health

            # Initial delay of 2 minutes before first check
            await asyncio.sleep(120)

            while True:
                try:
                    logger.info("🏥 Starting scheduled LLM provider health check...")
                    await check_llm_provider_health()
                except Exception as e:
                    logger.error(f"Health check error: {e}")

                # Wait 30 minutes before next check
                await asyncio.sleep(30 * 60)
        except Exception as e:
            logger.error(f"Health monitor startup error: {e}")

    # Schedule background startup task and do not await it here so the server can bind immediately
    bg_task = asyncio.create_task(run_startup_tasks())
    health_monitor_task = None if settings.ENABLE_MOCK_MODE else asyncio.create_task(schedule_health_monitor())

    try:
        logger.info("✅ Application startup complete")
        yield
    finally:
        logger.info("🛑 Initiating graceful shutdown...")

        if not bg_task.done():
            bg_task.cancel()
            try:
                await bg_task
            except asyncio.CancelledError:
                logger.debug("Cancelled background startup task")

        # Cancel health monitor task if running
        if health_monitor_task and not health_monitor_task.done():
            health_monitor_task.cancel()
            try:
                await health_monitor_task
            except asyncio.CancelledError:
                logger.debug("Cancelled LLM health monitor task")

        # Close database connections
        try:
            async with AsyncSessionLocal() as db:
                await db.close()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

        logger.info("✅ Shutdown complete")


async def create_default_admin():
    """Create a default admin user if no users exist"""
    try:
        from sqlalchemy import select

        from app.models.database import User

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            if not users:
                # Create default admin user
                admin_user = User(email="admin@bylix.email", full_name="System Administrator")
                admin_user.set_password("admin123")
                admin_user.is_verified = True
                admin_user.is_active = True
                db.add(admin_user)
                await db.commit()
                logger.warning("Default development administrator created", extra={"email": "admin@bylix.email"})
    except Exception as e:
        logger.warning(f"⚠️ Could not create default admin: {e}")


# Flag that indicates background startup tasks completed successfully
startup_ready = False

# Get environment variables
debug_mode = os.environ.get("DEBUG", "False").lower() == "true"
port = int(os.environ.get("PORT", 8000))

# Allowed origins - UPDATED with Vercel frontend and wildcards
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Vercel frontend URLs
    "https://bylix.email",
    "https://*.vercel.app",
    # Railway URLs (your current backend)
    "https://sunny-recreation-production.up.railway.app",
    "https://*.railway.app",
    # Render URLs (if you use it in future)
    "https://*.render.com",
    # Netlify URLs
    "https://*.netlify.app",
]

# Also get allowed origins from environment variable for flexibility
env_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "")
if env_allowed_origins:
    additional_origins = [origin.strip() for origin in env_allowed_origins.split(",") if origin.strip()]
    allowed_origins.extend(additional_origins)
    logger.info(f"🔧 Additional origins from environment: {additional_origins}")

# Remove duplicates
allowed_origins = list(set(allowed_origins))

logger.info(f"🔧 Starting on port: {port}")
logger.info(f"🔧 Debug mode: {debug_mode}")
logger.info(f"🔧 Allowed CORS origins: {len(allowed_origins)} configured")

app = FastAPI(
    title="Bylix Email",
    description="AI-powered Email Intelligence Platform with structured communication workflows and automation",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
register_request_logging(app)
register_debug_error_endpoint(app)
# ENHANCED CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "*",
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Origin",
    ],
    expose_headers=["*"],
    max_age=3600,  # Increase max age for better performance
)

register_exception_handlers(app)
registered_routers = set(register_routers(app))
app.include_router(
    create_system_router(
        RuntimeContext(
            allowed_origins=allowed_origins,
            debug=debug_mode,
            port=port,
            registered_routers=registered_routers,
            is_ready=lambda: startup_ready,
        )
    )
)
if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("📧 Bylix Email - Backend Server")
    logger.info("=" * 70)
    logger.info("Host: 0.0.0.0")
    logger.info(f"Port: {port}")
    logger.info(f"Environment: {'development' if debug_mode else 'production'}")
    logger.info(f"CORS: {len(allowed_origins)} allowed origins")
    logger.info(
        f"Frontend URLs: {[origin for origin in allowed_origins if 'vercel' in origin or 'localhost' in origin]}"
    )
    logger.info("=" * 70)

    uvicorn.run(app, host="0.0.0.0", port=port, reload=debug_mode, log_level="info", access_log=True)
