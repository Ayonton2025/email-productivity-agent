"""
Multi-Provider Email Account Endpoints

Handles OAuth connection for multiple email providers (Gmail, Outlook, Yahoo)
with unified interface for account management.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_user
from app.models.database import User, UserEmailAccount, get_db
from app.services.multi_provider_service import MultiProviderService, EmailProvider
from app.services.gmail_ingestion_service import GmailIngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-providers", tags=["multi-provider"])


class ProviderConfigResponse(BaseModel):
    """Configuration for OAuth flow"""
    provider: str
    display_name: str
    auth_url: str
    scopes: list


@router.get("/config/{provider}", response_model=ProviderConfigResponse)
async def get_provider_config(provider: str):
    """
    Get OAuth configuration for a specific provider.
    
    Path Parameters:
    - provider: Provider name (gmail, outlook, yahoo)
    
    Response:
    {
        "provider": "outlook",
        "display_name": "Outlook",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "scopes": ["Mail.Read", "Mail.ReadWrite", "User.Read"]
    }
    """
    try:
        config = MultiProviderService.get_provider_config(provider)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown provider: {provider}"
            )
        
        return {
            "provider": provider.lower(),
            "display_name": config["display_name"],
            "auth_url": config["auth_url"],
            "scopes": config["scopes"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get provider config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get provider configuration"
        )


@router.post("/connect/{provider}")
async def connect_provider(
    provider: str,
    access_token: str = Query(..., description="OAuth access token from provider"),
    refresh_token: Optional[str] = Query(None, description="OAuth refresh token"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Connect a new email provider account.
    
    Path Parameters:
    - provider: Provider name (gmail, outlook, yahoo)
    
    Query Parameters:
    - access_token: OAuth 2.0 access token (required)
    - refresh_token: OAuth 2.0 refresh token (optional)
    
    Response:
    {
        "status": "success",
        "account": {
            "id": "account-id",
            "provider": "outlook",
            "email": "user@company.com",
            "status": "connected",
            "created_at": "2024-01-15T10:30:00",
            "total_emails": 150
        },
        "message": "Successfully connected Outlook account"
    }
    """
    try:
        # Validate provider
        if provider.lower() not in [p.value for p in EmailProvider]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}"
            )
        
        # Get provider instance
        provider_instance = MultiProviderService.get_provider(
            provider,
            access_token,
            refresh_token
        )
        
        if not provider_instance:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create provider instance"
            )
        
        # Verify credentials
        if not await provider_instance.authenticate():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid {provider} credentials"
            )
        
        # Get user email (provider-specific)
        user_email = "unknown@example.com"
        try:
            if provider.lower() == EmailProvider.GMAIL.value:
                from googleapiclient.discovery import build
                from google.oauth2.credentials import Credentials
                
                creds = Credentials(token=access_token)
                service = build("gmail", "v1", credentials=creds)
                profile = service.users().getProfile(userId="me").execute()
                user_email = profile.get("emailAddress", "unknown@example.com")
            
            elif provider.lower() == EmailProvider.OUTLOOK.value:
                import aiohttp  # type: ignore[import]
                
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    async with session.get("https://graph.microsoft.com/v1.0/me", headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            user_email = data.get("userPrincipalName", "unknown@example.com")
            
            elif provider.lower() == EmailProvider.YAHOO.value:
                import aiohttp  # type: ignore[import]
                
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    async with session.get("https://api.mail.yahoo.com/user", headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            user_email = data.get("email", "unknown@example.com")
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to get user email from {provider}: {e}")
        
        # Create or update email account
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.user_id == current_user.id,
                UserEmailAccount.provider == provider.lower(),
                UserEmailAccount.email == user_email
            )
        )
        
        account = result.scalars().first()
        
        if account:
            # Update existing account
            account.access_token = access_token
            account.refresh_token = refresh_token or account.refresh_token
            account.status = "connected"
            account.last_sync = None  # Reset to trigger fresh sync
        else:
            # Create new account
            import uuid
            from datetime import datetime
            from app.core.security import encrypt_credential
            
            account = UserEmailAccount(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                email=user_email,
                provider=provider.lower(),
                status="connected",
                access_token=access_token,
                refresh_token=refresh_token,
                created_at=datetime.utcnow(),
                total_emails=0
            )
            db.add(account)
        
        await db.commit()
        await db.refresh(account)
        
        logger.info(f"✅ Connected {provider} account: {user_email}")
        
        # Return account details
        return {
            "status": "success",
            "account": {
                "id": account.id,
                "provider": account.provider,
                "email": account.email,
                "status": account.status,
                "created_at": account.created_at.isoformat(),
                "total_emails": account.total_emails or 0
            },
            "message": f"Successfully connected {provider.capitalize()} account"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to connect {provider} account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect email account"
        )


@router.get("/accounts")
async def list_provider_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all connected email provider accounts for the current user.
    
    Response:
    {
        "accounts": [
            {
                "id": "account-id",
                "email": "user@gmail.com",
                "provider": "gmail",
                "status": "connected",
                "last_sync": "2024-01-15T10:30:00",
                "total_emails": 250
            }
        ]
    }
    """
    try:
        result = await db.execute(
            select(UserEmailAccount)
            .where(UserEmailAccount.user_id == current_user.id)
            .order_by(UserEmailAccount.created_at.desc())
        )
        
        accounts = result.scalars().all()
        
        return {
            "accounts": [
                {
                    "id": acc.id,
                    "email": acc.email,
                    "provider": acc.provider,
                    "status": acc.status,
                    "last_sync": acc.last_sync.isoformat() if acc.last_sync else None,
                    "total_emails": acc.total_emails or 0
                }
                for acc in accounts
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to list accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list accounts"
        )


@router.patch("/accounts/{account_id}/sync")
async def trigger_sync(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a sync for a specific email account.
    
    Path Parameters:
    - account_id: Email account ID
    
    Response:
    {
        "status": "success",
        "emails_synced": 25,
        "message": "Successfully synced account"
    }
    """
    try:
        # Get account
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        
        account = result.scalars().first()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # For Gmail, use GmailIngestionService
        if account.provider == EmailProvider.GMAIL.value:
            ingestion_service = GmailIngestionService(db)
            
            # Fetch emails
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(token=account.access_token)
            service = build("gmail", "v1", credentials=creds)
            
            messages = await ingestion_service.fetch_last_n_emails(service, 50)
            
            # Extract message IDs and parse emails
            message_ids = [msg.get("id") for msg in messages]
            parsed_emails = []
            for msg in messages:
                parsed = ingestion_service.parse_gmail_message(msg)
                parsed_emails.append(parsed)
            
            # Store emails with attachment extraction
            email_ids = await ingestion_service.store_emails(
                current_user.id,
                account_id,
                parsed_emails,
                gmail_service=service,  # Pass Gmail service for attachment download
                message_ids=message_ids  # Pass message IDs for attachment extraction
            )
            
            # Process with AI
            await ingestion_service.process_emails_with_ai(email_ids)
            
            # Update account
            account.total_emails = (account.total_emails or 0) + len(parsed_emails)
            await db.commit()
            
            logger.info(f"✅ Synced {len(parsed_emails)} emails from Gmail with attachments")
            
            return {
                "status": "success",
                "emails_synced": len(parsed_emails),
                "message": f"Successfully synced {len(parsed_emails)} emails"
            }
        
        else:
            # For other providers, use their provider instance
            provider_instance = MultiProviderService.get_provider(
                account.provider,
                account.access_token,
                account.refresh_token
            )
            
            if not provider_instance:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create provider instance"
                )
            
            # Fetch messages
            messages = await provider_instance.fetch_messages(50)
            
            # Update account
            account.total_emails = (account.total_emails or 0) + len(messages)
            await db.commit()
            
            logger.info(f"✅ Synced {len(messages)} emails from {account.provider}")
            
            return {
                "status": "success",
                "emails_synced": len(messages),
                "message": f"Successfully synced {len(messages)} emails"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to sync account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync account"
        )


@router.delete("/accounts/{account_id}")
async def disconnect_provider(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect an email provider account.
    
    Path Parameters:
    - account_id: Email account ID
    
    Response:
    {
        "status": "success",
        "message": "Account disconnected"
    }
    """
    try:
        # Get account
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.id == account_id,
                UserEmailAccount.user_id == current_user.id
            )
        )
        
        account = result.scalars().first()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Delete account (soft delete - keep emails)
        account.status = "disconnected"
        await db.commit()
        
        logger.info(f"✅ Disconnected {account.provider} account: {account.email}")
        
        return {
            "status": "success",
            "message": "Account disconnected successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to disconnect account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect account"
        )
