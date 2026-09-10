"""Health endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.database import get_db
from app.services.llm_service import LLMService

router = APIRouter()
# Preserve the established log category for compatibility with operational filters.
logger = get_logger("app.api.endpoints")


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    """Database health check"""
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "service": "db", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB health check failed: {str(e)}")


@router.get("/health/ai")
async def health_ai():
    """AI/LLM health check (degrades to mock mode if not configured)"""
    try:
        llm = LLMService()
        return await llm.health_check()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI health check failed: {str(e)}")


@router.get("/info")
async def api_info():
    return {
        "name": "Bylix Email API",
        "version": "2.0.0",
        "description": "AI-powered Email Intelligence Platform",
        "endpoints": {
            "auth": [
                "POST /auth/register",
                "POST /auth/login",
                "GET /auth/me",
                "POST /auth/logout",
                "POST /auth/refresh",
            ],
            "emails": [
                "GET /emails",
                "GET /emails/my-inbox",
                "GET /emails/{email_id}",
                "PUT /emails/{email_id}/category",
                "POST /emails/sync",
                "POST /emails/load-mock",
                "POST /emails/load-mock-if-empty",
                "POST /emails/{email_id}/generate-reply",
            ],
            "prompts": [
                "GET /prompts",
                "GET /prompts/my",
                "GET /system-prompts",
                "POST /prompts",
                "PUT /prompts/{prompt_id}",
                "DELETE /prompts/{prompt_id}",
                "POST /prompts/{prompt_id}/test",
            ],
            "agent": ["POST /agent/process", "POST /agent/chat", "WS /ws/agent"],
            "email_accounts": ["GET /email-accounts", "POST /email-accounts/gmail", "GET /debug/email-accounts"],
        },
    }
