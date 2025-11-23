from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.models.database import get_db
from app.models.user_models import User, UserEmailAccount
from app.services.email_provider_service import EmailProviderService
from app.core.config import settings
from datetime import datetime

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])
email_provider_service = EmailProviderService()

# Import and use the same authentication system as endpoints.py
from app.api.endpoints import verify_token

async def get_current_user_from_token(authorization: Optional[str] = Header(None)):
    """Get current user from token (compatible with endpoints.py auth)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Get user from database using the user_id from the token session
        from sqlalchemy import select
        
        async for db in get_db():
            result = await db.execute(select(User).where(User.id == session["user_id"]))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            return user
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.get("/connect/gmail/url")
async def get_gmail_connect_url(
    redirect_uri: str, 
    authorization: Optional[str] = Header(None)
):
    """Get Gmail OAuth URL for connection"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        auth_url = email_provider_service.get_gmail_auth_url(settings.GOOGLE_CLIENT_ID, redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/gmail")
async def connect_gmail_account(
    auth_data: dict,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Connect Gmail account using OAuth tokens"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        success = await email_provider_service.authenticate_gmail_with_token(
            auth_data.get('access_token'),
            auth_data.get('refresh_token')
        )
        
        if success:
            # Store email account in database
            email_account = UserEmailAccount(
                user_id=current_user.id,
                provider="gmail",
                email=auth_data.get('email'),
                access_token=auth_data.get('access_token'),
                refresh_token=auth_data.get('refresh_token'),
                token_expiry=auth_data.get('token_expiry'),
                is_primary=True
            )
            
            db.add(email_account)
            await db.commit()
            await db.refresh(email_account)
            
            return {
                "status": "success",
                "message": "Gmail account connected successfully",
                "account": email_account.to_dict()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Gmail authentication failed"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gmail")
async def connect_gmail_account_simple_post(
    auth_data: dict,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Connect Gmail account - simple POST endpoint for frontend compatibility"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        success = await email_provider_service.authenticate_gmail_with_token(
            auth_data.get('access_token'),
            auth_data.get('refresh_token')
        )
        
        if success:
            # Store email account in database
            email_account = UserEmailAccount(
                user_id=current_user.id,
                provider="gmail",
                email=auth_data.get('email'),
                access_token=auth_data.get('access_token'),
                refresh_token=auth_data.get('refresh_token'),
                token_expiry=auth_data.get('token_expiry'),
                is_primary=True
            )
            
            db.add(email_account)
            await db.commit()
            await db.refresh(email_account)
            
            return {
                "status": "success",
                "message": "Gmail account connected successfully",
                "account": email_account.to_dict()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Gmail authentication failed"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/gmail/code")
async def connect_gmail_account_with_code(
    auth_data: dict,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Connect Gmail account using OAuth authorization code"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        tokens = await email_provider_service.exchange_gmail_code(
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
            auth_data.get('code'),
            auth_data.get('redirect_uri')
        )
        
        success = await email_provider_service.authenticate_gmail_with_token(
            tokens['access_token'],
            tokens.get('refresh_token')
        )
        
        if success:
            # Store email account in database
            email_account = UserEmailAccount(
                user_id=current_user.id,
                provider="gmail",
                email=auth_data.get('email'),
                access_token=tokens['access_token'],
                refresh_token=tokens.get('refresh_token'),
                token_expiry=tokens.get('token_expiry'),
                is_primary=True
            )
            
            db.add(email_account)
            await db.commit()
            await db.refresh(email_account)
            
            return {
                "status": "success",
                "message": "Gmail account connected successfully",
                "account": email_account.to_dict(),
                "tokens": tokens
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Gmail authentication failed"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/gmail-legacy")
async def connect_gmail_account_legacy(
    auth_data: dict,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Connect Gmail account (legacy method)"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        success = await email_provider_service.authenticate_gmail(
            auth_data.get('credentials_file'),
            auth_data.get('token_file')
        )
        
        if success:
            # Store email account in database
            email_account = UserEmailAccount(
                user_id=current_user.id,
                provider="gmail",
                email=auth_data.get('email'),
                access_token=auth_data.get('access_token'),
                refresh_token=auth_data.get('refresh_token'),
                is_primary=True
            )
            
            db.add(email_account)
            await db.commit()
            await db.refresh(email_account)
            
            return {
                "status": "success",
                "message": "Gmail account connected successfully",
                "account": email_account.to_dict()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Gmail authentication failed"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/outlook")
async def connect_outlook_account(
    auth_data: dict,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Connect Outlook account"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        success = await email_provider_service.authenticate_outlook(
            auth_data.get('client_id'),
            auth_data.get('client_secret'),
            auth_data.get('tenant_id')
        )
        
        if success:
            email_account = UserEmailAccount(
                user_id=current_user.id,
                provider="outlook",
                email=auth_data.get('email'),
                access_token=auth_data.get('access_token'),
                is_primary=True
            )
            
            db.add(email_account)
            await db.commit()
            await db.refresh(email_account)
            
            return {
                "status": "success",
                "message": "Outlook account connected successfully",
                "account": email_account.to_dict()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Outlook authentication failed"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_user_email_accounts(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """Get user's connected email accounts"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        from sqlalchemy import select
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.user_id == current_user.id
            ).order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc())
        )
        accounts = result.scalars().all()
        return [account.to_dict() for account in accounts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{account_id}")
async def disconnect_email_account(
    account_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect email account"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        from sqlalchemy import select
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Email account not found")
        
        await db.delete(account)
        await db.commit()
        
        return {"message": "Email account disconnected successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{account_id}/sync")
async def sync_email_account(
    account_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Sync emails from connected account"""
    try:
        current_user = await get_current_user_from_token(authorization)
        
        from sqlalchemy import select
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Email account not found")
        
        # Sync emails using the provider service
        if account.provider == "gmail":
            emails = await email_provider_service.fetch_gmail_emails(50)
        elif account.provider == "outlook":
            emails = await email_provider_service.fetch_outlook_emails(50)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        # Process emails through AI pipeline
        from app.services.email_service import EmailService
        email_service = EmailService(db)
        
        processed_count = 0
        for email_data in emails:
            # Add user_id to email data
            email_data['user_id'] = current_user.id
            await email_service.process_single_email(email_data)
            processed_count += 1
        
        # Update last sync time
        account.last_sync = datetime.utcnow()
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Synced {processed_count} emails from {account.provider}",
            "account": account.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def email_accounts_health():
    """Health check for email accounts endpoints"""
    return {
        "status": "healthy",
        "service": "email-accounts",
        "endpoints": {
            "GET /api/v1/email-accounts": "Get user's email accounts",
            "POST /api/v1/email-accounts/gmail": "Connect Gmail account",
            "GET /api/v1/email-accounts/connect/gmail/url": "Get Gmail OAuth URL",
            "POST /api/v1/email-accounts/connect/gmail": "Connect Gmail with tokens",
            "POST /api/v1/email-accounts/connect/gmail/code": "Connect Gmail with code",
            "DELETE /api/v1/email-accounts/{account_id}": "Disconnect email account",
            "POST /api/v1/email-accounts/{account_id}/sync": "Sync email account"
        }
    }