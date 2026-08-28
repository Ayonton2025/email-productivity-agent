from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import get_db
from app.models.email_provider_models import EmailProviderConfig
from app.services.email_provider_service import EmailProviderService

router = APIRouter()
email_provider_service = EmailProviderService()


class GmailCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=4096)
    redirect_uri: str = Field(..., min_length=1, max_length=2048)


class GmailTokenRequest(BaseModel):
    access_token: str = Field(..., min_length=1, max_length=8192)
    refresh_token: str | None = Field(default=None, max_length=8192)
    email: str | None = Field(default=None, max_length=320)


class GmailLegacyRequest(BaseModel):
    credentials_file: str = Field(..., min_length=1, max_length=4096)
    token_file: str = Field(..., min_length=1, max_length=4096)


class OutlookAuthRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=512)
    client_secret: str = Field(..., min_length=1, max_length=4096)
    tenant_id: str = Field(..., min_length=1, max_length=512)


class ProviderAuthRequest(BaseModel):
    credentials: dict = Field(default_factory=dict)
    code: str | None = Field(default=None, min_length=1, max_length=4096)
    redirect_uri: str | None = Field(default=None, min_length=1, max_length=2048)
    access_token: str | None = Field(default=None, min_length=1, max_length=8192)
    refresh_token: str | None = Field(default=None, max_length=8192)
    email: str | None = Field(default=None, max_length=320)
    credentials_file: str | None = Field(default=None, min_length=1, max_length=4096)
    token_file: str | None = Field(default=None, min_length=1, max_length=4096)
    client_id: str | None = Field(default=None, min_length=1, max_length=512)
    client_secret: str | None = Field(default=None, min_length=1, max_length=4096)
    tenant_id: str | None = Field(default=None, min_length=1, max_length=512)


@router.get("/providers/gmail/auth-url")
async def get_gmail_auth_url(redirect_uri: str):
    """Get Gmail OAuth URL"""
    try:
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")

        auth_url = email_provider_service.get_gmail_auth_url(
            settings.GOOGLE_CLIENT_ID, redirect_uri
        )
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/gmail/authenticate")
async def authenticate_gmail_with_code(
    auth_data: GmailCodeRequest, db: AsyncSession = Depends(get_db)
):
    """Authenticate with Gmail using OAuth code"""
    try:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")

        tokens = await email_provider_service.exchange_gmail_code(
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
            auth_data.code,
            auth_data.redirect_uri,
        )

        # Verify the tokens work
        success = await email_provider_service.authenticate_gmail_with_token(
            tokens["access_token"], tokens.get("refresh_token")
        )

        if success:
            # Save provider config to database
            provider_config = EmailProviderConfig(
                provider="gmail",
                user_id="current_user",  # In real app, get from auth
                config_data={
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens.get("refresh_token"),
                    "token_expiry": tokens.get("token_expiry"),
                    "scopes": tokens.get("scopes"),
                },
            )
            db.add(provider_config)
            await db.commit()

            return {
                "status": "success",
                "message": "Gmail authentication successful",
                "tokens": tokens,
            }
        else:
            raise HTTPException(status_code=400, detail="Gmail authentication failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/gmail/authenticate-token")
async def authenticate_gmail_directly(
    auth_data: GmailTokenRequest, db: AsyncSession = Depends(get_db)
):
    """Authenticate with Gmail using direct token (for frontend OAuth)"""
    try:
        success = await email_provider_service.authenticate_gmail_with_token(
            auth_data.access_token, auth_data.refresh_token
        )

        if success:
            provider_config = EmailProviderConfig(
                provider="gmail",
                user_id="current_user",  # In real app, get from auth
                config_data={
                    "access_token": auth_data.access_token,
                    "refresh_token": auth_data.refresh_token,
                    "email": auth_data.email,
                },
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
async def authenticate_gmail_legacy(
    credentials: GmailLegacyRequest, db: AsyncSession = Depends(get_db)
):
    """Authenticate with Gmail (legacy method)"""
    try:
        success = await email_provider_service.authenticate_gmail(
            credentials.credentials_file, credentials.token_file
        )

        if success:
            # Save provider config to database
            provider_config = EmailProviderConfig(
                provider="gmail",
                user_id="current_user",  # In real app, get from auth
                config_data=credentials.model_dump(),
            )
            db.add(provider_config)
            await db.commit()

            return {"status": "success", "message": "Gmail authentication successful"}
        else:
            raise HTTPException(status_code=400, detail="Gmail authentication failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/outlook/authenticate")
async def authenticate_outlook(credentials: OutlookAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with Outlook"""
    try:
        success = await email_provider_service.authenticate_outlook(
            credentials.client_id, credentials.client_secret, credentials.tenant_id
        )

        if success:
            provider_config = EmailProviderConfig(
                provider="outlook", user_id="current_user", config_data=credentials.model_dump()
            )
            db.add(provider_config)
            await db.commit()

            return {"status": "success", "message": "Outlook authentication successful"}
        else:
            raise HTTPException(status_code=400, detail="Outlook authentication failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/{provider}/authenticate")
async def authenticate_provider(
    provider: str, credentials: ProviderAuthRequest, db: AsyncSession = Depends(get_db)
):
    """
    Generic provider authenticate route used by frontend ProviderConnection.
    """
    provider = (provider or "").lower()
    if provider == "gmail":
        # Token-first flow from frontend OAuth clients.
        if credentials.access_token:
            return await authenticate_gmail_directly(
                GmailTokenRequest(
                    access_token=credentials.access_token,
                    refresh_token=credentials.refresh_token,
                    email=credentials.email,
                ),
                db,
            )
        # Authorization-code flow.
        if credentials.code and credentials.redirect_uri:
            return await authenticate_gmail_with_code(
                GmailCodeRequest(code=credentials.code, redirect_uri=credentials.redirect_uri), db
            )
        # Legacy local flow fallback.
        if credentials.credentials_file and credentials.token_file:
            return await authenticate_gmail_legacy(
                GmailLegacyRequest(
                    credentials_file=credentials.credentials_file,
                    token_file=credentials.token_file,
                ),
                db,
            )
        raise HTTPException(
            status_code=422, detail="Gmail authentication credentials are incomplete"
        )
    if provider == "outlook":
        if credentials.client_id and credentials.client_secret and credentials.tenant_id:
            return await authenticate_outlook(
                OutlookAuthRequest(
                    client_id=credentials.client_id,
                    client_secret=credentials.client_secret,
                    tenant_id=credentials.tenant_id,
                ),
                db,
            )
        raise HTTPException(
            status_code=422, detail="Outlook authentication credentials are incomplete"
        )

    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


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
            "emails": processed_emails,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_providers(db: AsyncSession = Depends(get_db)):
    """Get configured email providers"""
    # Implementation to fetch from database
    return {"providers": []}
