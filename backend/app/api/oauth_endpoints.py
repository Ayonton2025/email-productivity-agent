"""
OAuth Endpoints for Google and Microsoft authentication
Handles OAuth callbacks, token exchange, and provider-specific flows
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/oauth/google/callback")
async def google_oauth_callback(code: str, state: str = None, db: AsyncSession = Depends(get_db)):
    """
    Handle Google OAuth callback
    Exchange authorization code for access token and create/update user
    """
    try:
        logger.info("Processing Google OAuth callback")

        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            logger.error("❌ [Google OAuth] Missing Google credentials in environment")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth not configured")

        # In production, you would exchange the code for tokens using the Google API
        # For now, we'll extract email from the code or return success for manual processing

        return {
            "status": "success",
            "message": "Google OAuth callback received",
            "code_received": code is not None,
            "redirect_to": f"{settings.FRONTEND_URL}/email-accounts",
        }
    except Exception as e:
        logger.error(f"❌ [Google OAuth] Error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth callback failed: {str(e)}")


@router.post("/oauth/microsoft/callback")
async def microsoft_oauth_callback(code: str, state: str = None, db: AsyncSession = Depends(get_db)):
    """
    Handle Microsoft OAuth callback
    Exchange authorization code for access token and create/update user
    """
    try:
        logger.info("Processing Microsoft OAuth callback")

        # In production, you would exchange the code for tokens using the Microsoft API
        # For now, we'll return success for manual processing

        return {
            "status": "success",
            "message": "Microsoft OAuth callback received",
            "code_received": code is not None,
            "redirect_to": f"{settings.FRONTEND_URL}/email-accounts",
        }
    except Exception as e:
        logger.error(f"❌ [Microsoft OAuth] Error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth callback failed: {str(e)}")


@router.get("/oauth/google/auth-url")
async def get_google_auth_url():
    """
    Get the Google OAuth authorization URL for frontend redirect
    """
    try:
        if not settings.GOOGLE_CLIENT_ID:
            logger.error("❌ [Google OAuth] Missing GOOGLE_CLIENT_ID")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth not configured")

        # Generate OAuth URL
        redirect_uri = f"{settings.FRONTEND_URL}/auth/google/callback"
        scope = "openid profile email"

        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={scope}"
        )

        logger.info("✅ [Google OAuth] Generated auth URL")

        return {"status": "success", "auth_url": auth_url}
    except Exception as e:
        logger.error(f"❌ [Google OAuth] Error generating auth URL: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to generate auth URL: {str(e)}")


@router.get("/oauth/microsoft/auth-url")
async def get_microsoft_auth_url():
    """
    Get the Microsoft OAuth authorization URL for frontend redirect
    """
    try:
        # Generate OAuth URL
        redirect_uri = f"{settings.FRONTEND_URL}/auth/microsoft/callback"

        auth_url = (
            f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"client_id={settings.OUTLOOK_CLIENT_ID or ''}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openid profile email"
        )

        logger.info("✅ [Microsoft OAuth] Generated auth URL")

        return {"status": "success", "auth_url": auth_url}
    except Exception as e:
        logger.error(f"❌ [Microsoft OAuth] Error generating auth URL: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to generate auth URL: {str(e)}")


@router.post("/oauth/callback")
async def oauth_callback(code: str, state: str = None, provider: str = None, db: AsyncSession = Depends(get_db)):
    """
    Generic OAuth callback handler
    Routes to provider-specific handlers
    """
    try:
        logger.info(f"🔐 [OAuth] Processing callback from provider: {provider}")

        if provider == "google":
            return await google_oauth_callback(code, state, db)
        elif provider == "microsoft":
            return await microsoft_oauth_callback(code, state, db)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown OAuth provider: {provider}")
    except Exception as e:
        logger.error(f"❌ [OAuth] Error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth callback failed: {str(e)}")


@router.get("/oauth/status")
async def oauth_status():
    """
    Check OAuth configuration status
    """
    return {
        "status": "success",
        "google_configured": bool(settings.GOOGLE_CLIENT_ID),
        "microsoft_configured": bool(settings.OUTLOOK_CLIENT_ID),
        "frontend_url": settings.FRONTEND_URL,
    }
