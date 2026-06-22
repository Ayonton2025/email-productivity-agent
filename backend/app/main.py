from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
import signal
import sys

load_dotenv()

# Configure structured logging
from app.core.logging_config import configure_logging
configure_logging()
logger = logging.getLogger(__name__)

logger.info("🔧 Starting FastAPI application...")

# Import your application components with error handling
try:
    from app.api.endpoints import router as api_router
    logger.debug("✅ api_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import api_router: {e}")
    api_router = None

try:
    from app.api.user_email_endpoints import router as user_email_router
    print("✅ user_email_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import user_email_router: {e}")
    user_email_router = None

try:
    from app.api.auth_endpoints import router as auth_router
    print("✅ auth_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import auth_router: {e}")
    auth_router = None

try:
    from app.api.oauth_endpoints import router as oauth_router
    print("✅ oauth_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import oauth_router: {e}")
    oauth_router = None

try:
    from app.api.auto_reply_endpoints import router as auto_reply_router
    print("✅ auto_reply_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import auto_reply_router: {e}")
    auto_reply_router = None

try:
    from app.api.insights_endpoints import router as insights_router
    print("✅ insights_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import insights_router: {e}")
    insights_router = None

try:
    from app.api.workflow_endpoints import router as workflow_router
    print("✅ workflow_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import workflow_router: {e}")
    workflow_router = None

try:
    from app.api.agent_endpoints import router as agent_router
    print("✅ agent_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import agent_router: {e}")
    agent_router = None

try:
    from app.api.campaign_endpoints import router as campaign_router
    print("✅ campaign_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import campaign_router: {e}")
    campaign_router = None

try:
    from app.api.billing_endpoints import router as billing_router
    print("✅ billing_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import billing_router: {e}")
    billing_router = None

try:
    from app.api.ai_endpoints import router as ai_router
    print("✅ ai_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ai_router: {e}")
    ai_router = None

try:
    from app.api.inbox_endpoints import router as inbox_router
    print("✅ inbox_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import inbox_router: {e}")
    inbox_router = None

try:
    from app.api.webhook_endpoints import router as webhook_router
    print("✅ webhook_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import webhook_router: {e}")
    webhook_router = None

try:
    from app.api.realtime_endpoints import router as realtime_router
    print("✅ realtime_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import realtime_router: {e}")
    realtime_router = None

try:
    from app.api.sync_history_endpoints import router as sync_history_router
    print("✅ sync_history_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import sync_history_router: {e}")
    sync_history_router = None

try:
    from app.api.bulk_email_endpoints import router as bulk_email_router
    print("✅ bulk_email_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import bulk_email_router: {e}")
    bulk_email_router = None

try:
    from app.api.search_endpoints import router as search_router
    print("✅ search_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import search_router: {e}")
    search_router = None

try:
    from app.api.multi_provider_endpoints import router as multi_provider_router
    logger.info("✅ multi_provider_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import multi_provider_router: {e}")
    multi_provider_router = None

try:
    from app.api.email_provider_endpoints import router as email_provider_router
    logger.info("✅ email_provider_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import email_provider_router: {e}")
    email_provider_router = None

try:
    from app.api.analytics_endpoints import router as analytics_router
    logger.info("✅ analytics_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import analytics_router: {e}")
    analytics_router = None

try:
    from app.api.contact_endpoints import router as contact_router
    logger.info("✅ contact_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import contact_router: {e}")
    contact_router = None

try:
    from app.api.briefing_endpoints import router as briefing_router
    logger.info("✅ briefing_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import briefing_router: {e}")
    briefing_router = None

try:
    from app.api.followup_endpoints import router as followup_router
    logger.info("✅ followup_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import followup_router: {e}")
    followup_router = None

try:
    from app.api.hosted_email_endpoints import router as hosted_email_router
    logger.info("✅ hosted_email_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import hosted_email_router: {e}")
    hosted_email_router = None

try:
    from app.api.shared_inbox_endpoints import router as shared_inbox_router
    logger.info("✅ shared_inbox_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import shared_inbox_router: {e}")
    shared_inbox_router = None

try:
    from app.api.deliverability_endpoints import router as deliverability_router
    logger.info("✅ deliverability_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import deliverability_router: {e}")
    deliverability_router = None

try:
    from app.api.executive_endpoints import router as executive_router
    logger.info("✅ executive_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import executive_router: {e}")
    executive_router = None

try:
    from app.api.admin_llm_endpoints import router as admin_llm_router
    logger.info("✅ admin_llm_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import admin_llm_router: {e}")
    admin_llm_router = None

try:
    from app.api.admin_usage_endpoints import router as admin_usage_router
    logger.info("✅ admin_usage_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import admin_usage_router: {e}")
    admin_usage_router = None

try:
    from app.api.usage_endpoints import router as usage_router
    logger.info("✅ usage_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import usage_router: {e}")
    usage_router = None

try:
    from app.api.meeting_endpoints import router as meeting_router
except ImportError as e:
    logger.error(f"❌ Failed to import meeting_router: {e}")
    meeting_router = None

try:
    from app.api.voice_endpoints import router as voice_router
except ImportError as e:
    logger.error(f"❌ Failed to import voice_router: {e}")
    voice_router = None

try:
    from app.api.security_endpoints import router as security_router
except ImportError as e:
    logger.error(f"❌ Failed to import security_router: {e}")
    security_router = None

try:
    from app.api.legal_endpoints import router as legal_router
except ImportError as e:
    logger.error(f"❌ Failed to import legal_router: {e}")
    legal_router = None

try:
    from app.api.knowledge_endpoints import router as knowledge_router
except ImportError as e:
    logger.error(f"❌ Failed to import knowledge_router: {e}")
    knowledge_router = None

try:
    from app.api.language_endpoints import router as language_router
except ImportError as e:
    logger.error(f"❌ Failed to import language_router: {e}")
    language_router = None

try:
    from app.api.persona_endpoints import router as persona_router
except ImportError as e:
    logger.error(f"❌ Failed to import persona_router: {e}")
    persona_router = None

try:
    from app.api.task_manager_endpoints import router as task_manager_router
except ImportError as e:
    logger.error(f"❌ Failed to import task_manager_router: {e}")
    task_manager_router = None

try:
    from app.api.priority_endpoints import router as priority_router
except ImportError as e:
    logger.error(f"❌ Failed to import priority_router: {e}")
    priority_router = None

try:
    from app.api.sales_endpoints import router as sales_router
except ImportError as e:
    logger.error(f"❌ Failed to import sales_router: {e}")
    sales_router = None

try:
    from app.api.social_endpoints import router as social_router
except ImportError as e:
    logger.error(f"❌ Failed to import social_router: {e}")
    social_router = None

try:
    from app.api.timeline_endpoints import router as timeline_router
except ImportError as e:
    logger.error(f"❌ Failed to import timeline_router: {e}")
    timeline_router = None

try:
    from app.api.offline_endpoints import router as offline_router
except ImportError as e:
    logger.error(f"❌ Failed to import offline_router: {e}")
    offline_router = None

try:
    from app.api.ethics_endpoints import router as ethics_router
except ImportError as e:
    logger.error(f"❌ Failed to import ethics_router: {e}")
    ethics_router = None

try:
    from app.api.simulator_endpoints import router as simulator_router
except ImportError as e:
    logger.error(f"❌ Failed to import simulator_router: {e}")
    simulator_router = None

try:
    from app.api.support_endpoints import router as support_router
except ImportError as e:
    logger.error(f"❌ Failed to import support_router: {e}")
    support_router = None

try:
    from app.api.attachment_endpoints import router as attachment_router
    from app.api.attachment_endpoints import email_attachment_router
    logger.info("✅ attachment_router imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import attachment_router: {e}")
    attachment_router = None
    email_attachment_router = None

from app.models.database import init_db, AsyncSessionLocal
from app.services.prompt_service import PromptService
from app.services.llm_provider_config_service import LLMProviderConfigService
from app.core.config import settings
from app.core.security import get_password_hash

secret_issues = settings.validate_critical_secrets()
if secret_issues:
    runtime_env = (os.getenv("ENV", "development") or "development").strip().lower()
    enforce_secret_validation = runtime_env in {"production", "prod"} and not settings.DEBUG
    if enforce_secret_validation:
        raise RuntimeError(
            "Invalid security configuration in environment: "
            + "; ".join(secret_issues)
        )
    logger.warning(
        "⚠️ Non-production secret validation warnings: %s",
        "; ".join(secret_issues),
    )

# Flag that indicates background startup tasks completed successfully
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
        import os
        from sqlalchemy import text
        skip_init = os.environ.get("SKIP_DB_INIT", "false").lower() == "true"
        max_retries = 10
        delay = 3

        # If SKIP_DB_INIT is true, only verify DB connectivity and mark service ready
        if skip_init:
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"🔎 SKIP_DB_INIT=true; verifying DB connectivity (attempt {attempt})...")
                    async with AsyncSessionLocal() as db:
                        await db.execute(text("SELECT 1"))
                        # Ensure the 'users' table exists before marking ready
                        res = await db.execute(text("SELECT to_regclass('public.users')"))
                        table_exists = res.scalar_one_or_none()
                        if table_exists:
                            globals()['startup_ready'] = True
                            print("✅ DB reachable and schema present; startup marked ready (SKIP_DB_INIT)")
                            return
                        else:
                            print("⚠️ DB reachable but schema missing; waiting for init_db to run")
                            # Allow retries to continue to give init_db time to run
                except Exception as e:
                    print(f"⚠️ DB connectivity check failed (attempt {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, 30)
                    else:
                        print("❌ Exhausted DB retries; continuing without blocking server")
                        return

        for attempt in range(1, max_retries + 1):
            try:
                print(f"📦 Attempting DB initialization (attempt {attempt})...")
                await init_db()
                print("✅ Database initialized successfully (background)")

                # Initialize default prompts using a DB session
                try:
                    async with AsyncSessionLocal() as db:
                        prompt_service = PromptService(db)
                        await prompt_service.initialize_default_prompts()
                    print("✅ Default prompts created (background)")
                except Exception as prompt_error:
                    print(f"⚠️ Could not initialize default prompts: {prompt_error}")

                # Create default admin user if not exists
                await create_default_admin()
                # Mark startup as ready for readiness probes
                globals()['startup_ready'] = True
                print("✅ Background startup tasks completed, service is ready")
                return
            except Exception as e:
                print(f"⚠️ Background startup attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30)
                else:
                    print("❌ Exhausted startup retries; continuing without blocking server")
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
    health_monitor_task = asyncio.create_task(schedule_health_monitor())

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
                admin_user = User(
                    email="admin@bylix.email",
                    full_name="System Administrator"
                )
                admin_user.set_password("admin123")
                admin_user.is_verified = True
                admin_user.is_active = True
                db.add(admin_user)
                await db.commit()
                logger.info("✅ Default admin user created: admin@bylix.email / admin123")
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
    openapi_url="/openapi.json"
)

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
        "Access-Control-Allow-Origin"
    ],
    expose_headers=["*"],
    max_age=3600  # Increase max age for better performance
)

# Register API endpoints with error handling
if auth_router:
    app.include_router(auth_router, prefix="/api/v1", tags=["authentication"])
    print("✅ auth_router registered successfully")
else:
    print("❌ auth_router not available - authentication endpoints will not work")

if api_router:
    app.include_router(api_router, prefix="/api/v1", tags=["api"])
    print("✅ api_router registered successfully")
else:
    print("❌ api_router not available")

if user_email_router:
    app.include_router(user_email_router, prefix="/api/v1", tags=["email-accounts"])
    print("✅ user_email_router registered successfully")
else:
    print("❌ user_email_router not available")

if oauth_router:
    app.include_router(oauth_router, prefix="/api/v1", tags=["oauth"])
    print("✅ oauth_router registered successfully")
else:
    print("❌ oauth_router not available")

if auto_reply_router:
    app.include_router(auto_reply_router, prefix="/api/v1")
    print("✅ auto_reply_router registered successfully")
else:
    print("❌ auto_reply_router not available")

if insights_router:
    app.include_router(insights_router, prefix="/api/v1")
    print("✅ insights_router registered successfully")
else:
    print("❌ insights_router not available")

if workflow_router:
    app.include_router(workflow_router, prefix="/api/v1")
    print("✅ workflow_router registered successfully")
else:
    print("❌ workflow_router not available")

if agent_router:
    app.include_router(agent_router, prefix="/api/v1")
    print("✅ agent_router registered successfully")
else:
    print("❌ agent_router not available")

if campaign_router:
    app.include_router(campaign_router, prefix="/api/v1")
    print("✅ campaign_router registered successfully")
else:
    print("❌ campaign_router not available")

if billing_router:
    app.include_router(billing_router)
    print("✅ billing_router registered successfully")
else:
    print("❌ billing_router not available")

if ai_router:
    app.include_router(ai_router)
    print("✅ ai_router registered successfully")
else:
    print("❌ ai_router not available")

if inbox_router:
    app.include_router(inbox_router, prefix="/api/v1")
    print("✅ inbox_router registered successfully")
else:
    print("❌ inbox_router not available")

if webhook_router:
    app.include_router(webhook_router, prefix="/api/v1")
    print("✅ webhook_router registered successfully")
else:
    print("❌ webhook_router not available")

if realtime_router:
    app.include_router(realtime_router)
    print("✅ realtime_router (WebSocket) registered successfully")
else:
    print("❌ realtime_router not available")

if sync_history_router:
    app.include_router(sync_history_router, prefix="/api/v1")
    print("✅ sync_history_router registered successfully")
else:
    print("❌ sync_history_router not available")

if bulk_email_router:
    app.include_router(bulk_email_router, prefix="/api/v1")
    print("✅ bulk_email_router registered successfully")
else:
    print("❌ bulk_email_router not available")

if search_router:
    app.include_router(search_router, prefix="/api/v1")
    print("✅ search_router registered successfully")
else:
    print("❌ search_router not available")

if multi_provider_router:
    app.include_router(multi_provider_router, prefix="/api/v1")
    print("✅ multi_provider_router registered successfully")
else:
    print("❌ multi_provider_router not available")

if email_provider_router:
    app.include_router(email_provider_router, prefix="/api/v1")
    print("✅ email_provider_router registered successfully")
else:
    print("❌ email_provider_router not available")

if analytics_router:
    app.include_router(analytics_router, prefix="/api/v1")
    print("✅ analytics_router registered successfully")
else:
    print("❌ analytics_router not available")

if contact_router:
    app.include_router(contact_router, prefix="/api/v1")
    print("✅ contact_router registered successfully")
else:
    print("❌ contact_router not available")

if briefing_router:
    app.include_router(briefing_router, prefix="/api/v1")
    print("✅ briefing_router registered successfully")
else:
    print("❌ briefing_router not available")

if followup_router:
    app.include_router(followup_router, prefix="/api/v1")
    print("✅ followup_router registered successfully")
else:
    print("❌ followup_router not available")

if hosted_email_router:
    app.include_router(hosted_email_router, prefix="/api/v1")
    print("✅ hosted_email_router registered successfully")
else:
    print("❌ hosted_email_router not available")

if shared_inbox_router:
    app.include_router(shared_inbox_router, prefix="/api/v1")
    print("✅ shared_inbox_router registered successfully")
else:
    print("❌ shared_inbox_router not available")

if deliverability_router:
    app.include_router(deliverability_router, prefix="/api/v1")
    print("✅ deliverability_router registered successfully")
else:
    print("❌ deliverability_router not available")

if executive_router:
    app.include_router(executive_router, prefix="/api/v1")
    print("✅ executive_router registered successfully")
else:
    print("❌ executive_router not available")

if admin_llm_router:
    app.include_router(admin_llm_router)
    print("✅ admin_llm_router registered successfully")
else:
    print("❌ admin_llm_router not available")

if admin_usage_router:
    app.include_router(admin_usage_router)
    print("✅ admin_usage_router registered successfully")
else:
    print("❌ admin_usage_router not available")

if usage_router:
    app.include_router(usage_router)
    print("✅ usage_router registered successfully")
else:
    print("❌ usage_router not available")

if meeting_router:
    app.include_router(meeting_router, prefix="/api/v1")
if voice_router:
    app.include_router(voice_router, prefix="/api/v1")
if security_router:
    app.include_router(security_router, prefix="/api/v1")
if legal_router:
    app.include_router(legal_router, prefix="/api/v1")
if knowledge_router:
    app.include_router(knowledge_router, prefix="/api/v1")
if language_router:
    app.include_router(language_router, prefix="/api/v1")
if persona_router:
    app.include_router(persona_router, prefix="/api/v1")
if task_manager_router:
    app.include_router(task_manager_router, prefix="/api/v1")
if priority_router:
    app.include_router(priority_router, prefix="/api/v1")
if sales_router:
    app.include_router(sales_router, prefix="/api/v1")
if social_router:
    app.include_router(social_router, prefix="/api/v1")
if timeline_router:
    app.include_router(timeline_router, prefix="/api/v1")
if offline_router:
    app.include_router(offline_router, prefix="/api/v1")
if ethics_router:
    app.include_router(ethics_router, prefix="/api/v1")
if simulator_router:
    app.include_router(simulator_router, prefix="/api/v1")
if support_router:
    app.include_router(support_router, prefix="/api/v1")

if attachment_router:
    app.include_router(attachment_router, prefix="/api/v1")
    logger.info("✅ attachment_router registered successfully")
else:
    logger.error("❌ attachment_router not available")

if email_attachment_router:
    app.include_router(email_attachment_router, prefix="/api/v1")
    logger.info("✅ email_attachment_router registered successfully")
else:
    logger.error("❌ email_attachment_router not available")

# Add a simple test endpoint that doesn't depend on imports
@app.post("/api/v1/test-register")
async def test_register():
    """Test registration endpoint"""
    return {
        "message": "Test endpoint working",
        "status": "success",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/test-auth")
async def test_auth():
    """Test auth endpoint"""
    return {
        "message": "Auth test endpoint working",
        "endpoints": {
            "register": "POST /api/v1/auth/register",
            "login": "POST /api/v1/auth/login",
            "me": "GET /api/v1/auth/me"
        }
    }

@app.get("/api/v1/test-cors")
async def test_cors():
    """Test CORS configuration"""
    return {
        "message": "CORS test endpoint",
        "cors_configured": True,
        "allowed_origins_count": len(allowed_origins),
        "timestamp": datetime.utcnow().isoformat()
    }

# Health check endpoint with detailed CORS info
@app.get("/health")
async def health_check():
    """
    Health check endpoint that verifies all critical dependencies.
    
    Returns detailed status including:
    - Database connectivity
    - Redis availability
    - Application readiness
    """
    try:
        health_status = {
            "status": "healthy",
            "service": "bylix-email-platform",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {}
        }
        
        # Check database connectivity
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
                health_status["dependencies"]["database"] = {
                    "status": "healthy",
                    "message": "PostgreSQL connected"
                }
        except Exception as db_error:
            health_status["dependencies"]["database"] = {
                "status": "unhealthy",
                "message": str(db_error)
            }
            health_status["status"] = "degraded"
        
        # Check Redis connectivity (if configured)
        try:
            import redis
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                socket_connect_timeout=3,
                decode_responses=True
            )
            r.ping()
            health_status["dependencies"]["redis"] = {
                "status": "healthy",
                "message": "Redis connected"
            }
        except Exception as redis_error:
            health_status["dependencies"]["redis"] = {
                "status": "warning",
                "message": f"Redis unavailable: {str(redis_error)}"
            }
        
        health_status["routers"] = {
            "auth": auth_router is not None,
            "api": api_router is not None,
            "email_accounts": user_email_router is not None,
            "inbox": inbox_router is not None,
            "webhook": webhook_router is not None,
            "realtime": realtime_router is not None,
            "sync_history": sync_history_router is not None,
            "search": search_router is not None,
            "multi_provider": multi_provider_router is not None
        }
        
        health_status["startup_ready"] = startup_ready
        health_status["cors"] = {
            "enabled": True,
            "allowed_origins_count": len(allowed_origins)
        }
        
        return health_status
    
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/api/v1/health")
async def health_check_api():
    """Health check endpoint for API v1"""
    return {
        "status": "healthy",
        "service": "bylix-email-platform",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "routers": {
            "auth": auth_router is not None,
            "api": api_router is not None,
            "email_accounts": user_email_router is not None
        },
        "cors": {
            "enabled": True,
            "allowed_origins_count": len(allowed_origins),
            "frontend_urls": [origin for origin in allowed_origins if "vercel" in origin or "localhost" in origin]
        }
    }

@app.get("/ready")
async def ready():
    """Readiness endpoint reporting when background initialization has completed"""
    if startup_ready:
        return {"status": "ready", "service": "bylix-email-platform"}
    return JSONResponse(status_code=503, content={"status": "starting", "service": "bylix-email-platform"})

@app.get("/")
async def root():
    return {
        "message": "Bylix Email API",
        "status": "running",
        "version": "2.0.0",
        "docs": "/docs",
        "api_base": "/api/v1",
        "environment": "development" if debug_mode else "production",
        "routers_loaded": {
            "auth": auth_router is not None,
            "api": api_router is not None,
            "email_accounts": user_email_router is not None
        },
        "cors_info": {
            "allowed_origins_count": len(allowed_origins),
            "frontend_domains": [origin for origin in allowed_origins if "vercel" in origin or "localhost" in origin]
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/info")
async def info():
    """Detailed system information"""
    return {
        "service": "Bylix Email Backend",
        "version": "2.0.0",
        "environment": "development" if debug_mode else "production",
        "debug_mode": debug_mode,
        "port": port,
        "cors": {
            "allowed_origins": allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        },
        "endpoints_available": {
            "authentication": auth_router is not None,
            "api": api_router is not None,
            "email_accounts": user_email_router is not None
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# CORS preflight and headers are handled by CORSMiddleware above. Removed custom OPTIONS handler and middleware to avoid duplicate headers.

if __name__ == "__main__":
    print("=" * 70)
    print("📧 Bylix Email - Backend Server")
    print("=" * 70)
    print(f"Host: 0.0.0.0")
    print(f"Port: {port}")
    print(f"Environment: {'development' if debug_mode else 'production'}")
    print(f"CORS: {len(allowed_origins)} allowed origins")
    print(f"Frontend URLs: {[origin for origin in allowed_origins if 'vercel' in origin or 'localhost' in origin]}")
    print("=" * 70)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=debug_mode,
        log_level="info",
        access_log=True
    )
