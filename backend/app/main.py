from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime

print("🔧 Starting FastAPI application...")

# Import your application components with error handling
try:
    from app.api.endpoints import router as api_router
    print("✅ api_router imported successfully")
except ImportError as e:
    print(f"❌ Failed to import api_router: {e}")
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

from app.models.database import init_db, AsyncSessionLocal
from app.services.prompt_service import PromptService
from app.core.config import settings
from app.core.security import get_password_hash

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Email Productivity Agent Backend...")
    print("📦 Initializing database...")
    try:
        await init_db()
        # Initialize default prompts using a DB session
        async with AsyncSessionLocal() as db:
            prompt_service = PromptService(db)
            await prompt_service.initialize_default_prompts()
        print("✅ Database initialized successfully")
        print("✅ Default prompts created")
        # Create default admin user if not exists
        await create_default_admin()
    except Exception as e:
        print(f"❌ Startup error: {e}")
        import traceback
        print(f"❌ Stack trace: {traceback.format_exc()}")
        if os.environ.get("DEBUG", "False").lower() == "true":
            raise
    yield
    # Shutdown
    print("🛑 Shutting down...")

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
                    email="admin@inboxai.com",
                    full_name="System Administrator"
                )
                admin_user.set_password("admin123")
                admin_user.is_verified = True
                admin_user.is_active = True
                db.add(admin_user)
                await db.commit()
                print("✅ Default admin user created: admin@inboxai.com / admin123")
    except Exception as e:
        print(f"⚠️ Could not create default admin: {e}")

# Get environment variables
debug_mode = os.environ.get("DEBUG", "False").lower() == "true"
port = int(os.environ.get("PORT", 8000))

# Allowed origins
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://email-productivity-agent.vercel.app",
    "https://sunny-recreation-production.up.railway.app"
]

print(f"🔧 Starting on port: {port}")
print(f"🔧 Debug mode: {debug_mode}")
print(f"🔧 Allowed origins: {allowed_origins}")

app = FastAPI(
    title="Email Productivity Agent",
    description="AI-powered email management system with user authentication and real email provider integration",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
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

# ... rest of your endpoints (health, info, etc.) remain the same
@app.get("/")
async def root():
    return {
        "message": "Email Productivity Agent API",
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
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "email-productivity-agent",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "routers": {
            "auth": auth_router is not None,
            "api": api_router is not None,
            "email_accounts": user_email_router is not None
        }
    }

# ... rest of your existing endpoints

if __name__ == "__main__":
    print("=" * 70)
    print("📧 Email Productivity Agent - Backend Server")
    print("=" * 70)
    print(f"Host: 0.0.0.0")
    print(f"Port: {port}")
    print(f"Environment: {'development' if debug_mode else 'production'}")
    print("=" * 70)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=debug_mode,
        log_level="info",
        access_log=True
    )
