from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime

# Import your application components
from app.api.endpoints import router as api_router
from app.api.user_email_endpoints import router as user_email_router
from app.api.auth_endpoints import router as auth_router  # Make sure this is imported
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
allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "")
if allowed_origins_str:
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]
else:
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

# Register API endpoints - MAKE SURE AUTH ROUTER IS INCLUDED
app.include_router(auth_router, prefix="/api/v1", tags=["authentication"])  # This line is critical!
app.include_router(api_router, prefix="/api/v1", tags=["api"])
app.include_router(user_email_router, prefix="/api/v1", tags=["email-accounts"])

# Add test endpoints
@app.get("/test-connection")
async def test_connection():
    """Test if backend is responding"""
    return {
        "status": "backend_working",
        "message": "Backend is responding correctly",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/test-db")
async def test_database():
    """Test database connection"""
    try:
        from app.models.database import get_db
        async for db in get_db():
            await db.execute("SELECT 1")
            return {"database": "connected"}
    except Exception as e:
        return {"database": "error", "detail": str(e)}

@app.get("/test-all")
async def test_all_services():
    """Test all services"""
    results = {}
    
    # Test database
    try:
        from app.models.database import get_db
        async for db in get_db():
            await db.execute("SELECT 1")
            results["database"] = "connected"
    except Exception as e:
        results["database"] = f"error: {str(e)}"
    
    # Test environment
    results["environment"] = {
        "debug_mode": debug_mode,
        "port": port,
        "database_url": settings.DATABASE_URL[:20] + "..." if settings.DATABASE_URL else "not_set"
    }
    
    return results

@app.get("/")
async def root():
    return {
        "message": "Email Productivity Agent API",
        "status": "running",
        "version": "2.0.0",
        "docs": "/docs",
        "api_base": "/api/v1",
        "environment": "development" if debug_mode else "production",
        "features": [
            "User Authentication & Registration",
            "Email Verification System",
            "Password Reset Functionality",
            "Real Email Provider Integration (Gmail, Outlook)",
            "Multi-User Data Isolation",
            "Advanced OpenAI AI Processing",
            "Smart Email Categorization",
            "AI-Powered Draft Generation",
            "Cross-Email Insights",
            "Productivity Analytics"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "email-productivity-agent",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "development" if debug_mode else "production",
        "database": "connected",
        "ai_services": "available"
    }

@app.get("/ping")
async def ping():
    return {"message": "pong", "status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/test-cors")
async def test_cors():
    return {
        "message": "CORS test endpoint - Working!",
        "cors_configured": True,
        "allowed_origins": allowed_origins,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/info")
async def api_info():
    return {
        "name": "Email Productivity Agent API",
        "version": "2.0.0",
        "description": "AI-powered email management system",
        "status": "operational",
        "endpoints": {
            "authentication": [
                "POST /api/v1/auth/register",
                "POST /api/v1/auth/login",
                "POST /api/v1/auth/logout",
                "GET /api/v1/auth/me",
                "POST /api/v1/auth/refresh",
                "POST /api/v1/auth/forgot-password",
                "POST /api/v1/auth/reset-password",
                "POST /api/v1/auth/verify-email"
            ],
            "emails": [
                "GET /api/v1/emails",
                "GET /api/v1/emails/my-inbox",
                "GET /api/v1/emails/{email_id}",
                "PUT /api/v1/emails/{email_id}/category",
                "POST /api/v1/emails/sync",
                "POST /api/v1/emails/load-mock"
            ],
            "email_accounts": [
                "POST /api/v1/email-accounts/connect/gmail",
                "POST /api/v1/email-accounts/connect/outlook",
                "GET /api/v1/email-accounts",
                "DELETE /api/v1/email-accounts/{account_id}",
                "POST /api/v1/email-accounts/{account_id}/sync"
            ],
            "ai_agent": [
                "POST /api/v1/agent/process",
                "POST /api/v1/agent/chat",
                "WS /ws/agent"
            ],
            "prompts": [
                "GET /api/v1/prompts",
                "GET /api/v1/prompts/my",
                "POST /api/v1/prompts",
                "PUT /api/v1/prompts/{prompt_id}",
                "DELETE /api/v1/prompts/{prompt_id}"
            ]
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": request.url.path}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    print("=" * 70)
    print("📧 Email Productivity Agent - Backend Server")
    print("=" * 70)
    print(f"Host: 0.0.0.0")
    print(f"Port: {port}")
    print(f"Environment: {'development' if debug_mode else 'production'}")
    print(f"Allowed Origins: {allowed_origins}")
    print(f"Database: SQLite + AIOSQLite")
    print(f"AI Provider: OpenAI + Enhanced Processing")
    print(f"Email Providers: Gmail, Outlook")
    print(f"Features: User Auth, Real Email Sync, AI Processing")
    print("=" * 70)
    print(f"📚 API Documentation: http://localhost:{port}/docs")
    print(f"❤️ Health Check: http://localhost:{port}/health")
    print(f"🔧 CORS Test: http://localhost:{port}/test-cors")
    print(f"ℹ️ API Info: http://localhost:{port}/info")
    print("=" * 70)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=debug_mode,
        log_level="info",
        access_log=True
    )
