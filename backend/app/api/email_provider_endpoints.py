from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.models.database import get_db
from app.services.email_provider_service import EmailProviderService
from app.models.email_provider_models import EmailProviderConfig, SyncHistory
from app.core.config import settings

router = APIRouter()
email_provider_service = EmailProviderService()

@router.get("/providers/gmail/auth-url")
async def get_gmail_auth_url(redirect_uri: str):
    """Get Gmail OAuth URL"""
    try:
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        auth_url = email_provider_service.get_gmail_auth_url(settings.GOOGLE_CLIENT_ID, redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/providers/gmail/authenticate")
async def authenticate_gmail_with_code(auth_data: dict, db: AsyncSession = Depends(get_db)):
    """Authenticate with Gmail using OAuth code"""
    try:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        tokens = await email_provider_service.exchange_gmail_code(
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
            auth_data.get('code'),
            auth_data.get('redirect_uri')
        )
        
        # Verify the tokens work
        success = await email_provider_service.authenticate_gmail_with_token(
            tokens['access_token'],
            tokens.get('refresh_token')
        )
        
        if success:
            # Save provider config to database
            provider_config = EmailProviderConfig(
                provider="gmail",
                user_id="current_user",  # In real app, get from auth
                config_data={
                    'access_token': tokens['access_token'],
                    'refresh_token': tokens.get('refresh_token'),
                    'token_expiry': tokens.get('token_expiry'),
                    'scopes': tokens.get('scopes')
                }
            )
            db.add(provider_config)
            await db.commit()
            
            return {
                "status": "success", 
                "message": "Gmail authentication successful",
                "tokens": tokens
            }
        else:
            raise HTTPException(status_code=400, detail="Gmail authentication failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/providers/gmail/authenticate-token")
async def authenticate_gmail_directly(auth_data: dict, db: AsyncSession = Depends(get_db)):
    """Authenticate with Gmail using direct token (for frontend OAuth)"""
    try:
        success = await email_provider_service.authenticate_gmail_with_token(
            auth_data.get('access_token'),
            auth_data.get('refresh_token')
        )
        
        if success:
            provider_config = EmailProviderConfig(
                provider="gmail",
                user_id="current_user",  # In real app, get from auth
                config_data={
                    'access_token': auth_data.get('access_token'),
                    'refresh_token': auth_data.get('refresh_token'),
                    'email': auth_data.get('email')
                }
            )
            db.add(provider_config)
            await db.commit()
            
            return {"status": "success", "message": "Gmail authentication successful"}
        else:
            raise HTTPException(status_code=400, detail="Gmail authentication failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoint for backward compatibility
@router.post("/providers/gmail/authenticate-legacy")
async def authenticate_gmail_legacy(credentials: dict, db: AsyncSession = Depends(get_db)):
    """Authenticate with Gmail (legacy method)"""
    try:
        success = await email_provider_service.authenticate_gmail(
            credentials.get('credentials_file'),
            credentials.get('token_file')
        )
        
        if success:
            # Save provider config to database
            provider_config = EmailProviderConfig(
                provider="gmail",
                user_id="current_user",  # In real app, get from auth
                config_data=credentials
            )
            db.add(provider_config)
            await db.commit()
            
            return {"status": "success", "message": "Gmail authentication successful"}
        else:
            raise HTTPException(status_code=400, detail="Gmail authentication failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/providers/outlook/authenticate")
async def authenticate_outlook(credentials: dict, db: AsyncSession = Depends(get_db)):
    """Authenticate with Outlook"""
    try:
        success = await email_provider_service.authenticate_outlook(
            credentials.get('client_id'),
            credentials.get('client_secret'),
            credentials.get('tenant_id')
        )
        
        if success:
            provider_config = EmailProviderConfig(
                provider="outlook",
                user_id="current_user",
                config_data=credentials
            )
            db.add(provider_config)
            await db.commit()
            
            return {"status": "success", "message": "Outlook authentication successful"}
        else:
            raise HTTPException(status_code=400, detail="Outlook authentication failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/providers/{provider}/sync")
async def sync_emails(provider: str, max_results: int = 50, db: AsyncSession = Depends(get_db)):
    """Sync emails from provider"""
    try:
        if provider == "gmail":
            emails = await email_provider_service.fetch_gmail_emails(max_results)
        elif provider == "outlook":
            emails = await email_provider_service.fetch_outlook_emails(max_results)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        # Process emails through AI pipeline
        processed_emails = []
        for email in emails:
            # Add to your existing email processing pipeline
            processed_emails.append(email)
        
        return {
            "status": "success",
            "message": f"Synced {len(processed_emails)} emails from {provider}",
            "emails": processed_emails
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers")
async def get_providers(db: AsyncSession = Depends(get_db)):
    """Get configured email providers"""
    # Implementation to fetch from database
    return {"providers": []}