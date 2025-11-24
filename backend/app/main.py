from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime

from app.api.endpoints import router as api_router
from app.api.user_email_endpoints import router as user_email_router
from app.models.database import init_db, AsyncSessionLocal
from app.services.prompt_service import PromptService

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
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        # Don't raise in production, just log
        if os.environ.get("DEBUG", "False").lower() == "true":
            raise
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")

# Get environment variables
debug_mode = os.environ.get("DEBUG", "False").lower() == "true"

# Get allowed origins from environment or use defaults
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
        "https://email-productivity-agent.vercel.app",  # ADDED: Your Vercel frontend
        "https://*.vercel.app",  # ADDED: All Vercel preview deployments
    ]

app = FastAPI(
    title="Email Productivity Agent",
    description="AI-powered email management system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS configuration - FIXED for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Credentials",
        "*"  # Fallback for any other headers
    ],
    expose_headers=["*"],
    max_age=600  # Cache preflight requests for 10 minutes
)

# Register all API endpoints under /api/v1/
app.include_router(api_router, prefix="/api/v1")
app.include_router(user_email_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Email Productivity Agent API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "api_base": "/api/v1",
        "environment": "development" if debug_mode else "production",
        "cors_enabled": True,
        "allowed_origins": allowed_origins
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "email-agent",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "development" if debug_mode else "production",
        "cors": {
            "enabled": True,
            "allowed_origins_count": len(allowed_origins)
        }
    }

@app.get("/test-cors")
async def test_cors():
    """Test endpoint to verify CORS is working"""
    return {
        "message": "CORS test endpoint",
        "cors_configured": True,
        "allowed_origins": allowed_origins,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify the API is working"""
    return {
        "message": "API is working!",
        "endpoints_available": True,
        "authentication_ready": True,
        "environment": "development" if debug_mode else "production",
        "cors_enabled": True
    }

@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    """Handle preflight OPTIONS requests for all paths"""
    return {
        "message": "Preflight request handled",
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        "allowed_headers": ["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
        "allow_credentials": True
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print("=" * 60)
    print("📧 Email Productivity Agent - Backend Server")
    print("=" * 60)
    print(f"Host: 0.0.0.0")
    print(f"Port: {port}")
    print(f"Environment: {'development' if debug_mode else 'production'}")
    print(f"Allowed Origins: {allowed_origins}")
    print(f"CORS Enabled: Yes")
    print(f"Docs: http://localhost:{port}/docs")
    print(f"Health: http://localhost:{port}/health")
    print(f"CORS Test: http://localhost:{port}/test-cors")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=debug_mode,
        log_level="info"
    )
