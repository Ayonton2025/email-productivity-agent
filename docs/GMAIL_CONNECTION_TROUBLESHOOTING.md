# Gmail Connection Troubleshooting Guide

## Issue: 500 Error When Connecting Gmail

### Problem Description
When attempting to connect a Gmail account with credentials (email, access token, refresh token), the frontend receives a 500 Internal Server Error from the backend endpoint: `POST /api/v1/email-accounts/gmail`

**Console Error:**
```
127.0.0.1:8000/api/v1/email-accounts/gmail:1 Failed to load resource: the server responded with a status of 500 (Internal Server Error)
```

## Root Cause Analysis

The original implementation had several issues:

1. **Invalid Request Body Parsing**: The endpoints were defined with `auth_data: dict` which FastAPI doesn't properly handle. FastAPI needs explicit Pydantic models for request body validation and deserialization.

2. **Poor Error Handling**: The original error handling didn't provide detailed error messages, making it difficult to debug authentication failures.

3. **Invalid Token Testing**: When a token is invalid or expired, the Gmail API returns an error that wasn't being properly caught and reported.

## Solution Applied

### 1. Created Pydantic Models for Request Validation

Added proper request models in `/backend/app/api/user_email_endpoints.py`:

```python
from pydantic import BaseModel
from typing import Optional

class GmailAuthData(BaseModel):
    email: str
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[str] = None

class OutlookAuthData(BaseModel):
    email: str
    access_token: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None

class GmailCodeAuthData(BaseModel):
    code: str
    redirect_uri: str
    email: Optional[str] = None

class GmailLegacyAuthData(BaseModel):
    email: str
    credentials_file: str
    token_file: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
```

### 2. Updated Endpoints to Use Pydantic Models

Changed all endpoint signatures from:
```python
async def connect_gmail_account_simple_post(
    auth_data: dict,  # ❌ Invalid
    ...
)
```

To:
```python
async def connect_gmail_account_simple_post(
    auth_data: GmailAuthData,  # ✅ Proper validation
    ...
)
```

### 3. Enhanced Error Logging

Updated `/backend/app/services/email_provider_service.py` to provide detailed debugging information:

```python
async def authenticate_gmail_with_token(self, access_token: str, refresh_token: str = None) -> bool:
    """Authenticate with Gmail using OAuth tokens"""
    try:
        print(f"🔐 [EmailProviderService] Authenticating with access_token: {access_token[:20] if access_token else 'None'}...")
        if not access_token:
            print("❌ [EmailProviderService] Access token is empty!")
            return False
        
        # ... rest of authentication ...
        
    except HttpError as error:
        print(f'❌ Gmail HTTP error: {error}')
        print(f'❌ Error details: {error.content if hasattr(error, "content") else "N/A"}')
        return False
    except Exception as e:
        print(f'❌ Gmail token validation error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        return False
```

### 4. Improved Endpoint Error Messages

Updated all endpoints to provide informative error responses:

```python
if success:
    # ... store account ...
    return {
        "status": "success",
        "message": "Gmail account connected successfully",
        "account": email_account.to_dict()
    }
else:
    raise HTTPException(
        status_code=400,
        detail="Gmail authentication failed - invalid access token"
    )
```

## How to Verify the Fix

### 1. Backend is Running
Check that the backend is running on `http://127.0.0.1:8000`:

```bash
curl http://127.0.0.1:8000/api/v1/email-accounts/health
```

You should see:
```json
{
  "status": "healthy",
  "service": "email-accounts",
  "endpoints": { ... }
}
```

### 2. Test Gmail Connection

Use the frontend form at **Email Accounts** → **Connect Gmail Account** and provide:
- **Gmail Address**: your-email@gmail.com
- **Access Token**: Your OAuth access token
- **Refresh Token**: Your OAuth refresh token (optional)

### 3. Monitor Backend Logs

The backend will now output detailed logs:

**Success:**
```
🔐 [Gmail Connection] Attempting to connect Gmail account: user@gmail.com
🔐 [Gmail Connection] Access token provided: True
🔐 [Gmail Connection] Refresh token provided: True
✅ [Gmail Connection] Gmail authentication successful for user@gmail.com
✅ [Gmail Connection] Email account stored in database with ID: <uuid>
```

**Failure:**
```
🔐 [Gmail Connection] Attempting to connect Gmail account: user@gmail.com
❌ [Gmail Connection] Gmail authentication failed for user@gmail.com
❌ [Gmail Connection] Error: invalid_grant: Token has been revoked.
```

## Common Issues and Solutions

### 1. "Gmail authentication failed - invalid access token"

**Cause:** The access token has expired or is invalid.

**Solution:**
- Ensure you're using a valid, unexpired OAuth token from Google
- If the token has expired, you need to refresh it or get a new one
- Check that the token has the required scopes:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/gmail.modify`

### 2. "Invalid request body"

**Cause:** The request doesn't match the expected Pydantic model.

**Solution:**
- Ensure the request includes all required fields:
  - `email` (required): Your Gmail address
  - `access_token` (required): Your OAuth access token
  - `refresh_token` (optional): Your OAuth refresh token
  - `token_expiry` (optional): Token expiration time

**Example Request:**
```json
{
  "email": "user@gmail.com",
  "access_token": "ya29.a0AfH6SMBx...",
  "refresh_token": "1//0gF...",
  "token_expiry": "2026-01-19T21:30:00"
}
```

### 3. Backend returns 500 with no details

**Cause:** Uncaught exception in request handling.

**Solution:**
- Check the backend logs for the full error traceback
- The backend will now print detailed information about what went wrong
- Look for lines starting with `❌` in the logs

## Obtaining Gmail OAuth Tokens

If you don't have OAuth tokens yet:

### Option 1: Using Google OAuth Playground
1. Go to https://developers.google.com/oauthplayground
2. Select Gmail API v1 scopes
3. Follow the authorization flow
4. Copy the generated access token (and refresh token if available)

### Option 2: Using Google Cloud Console
1. Create a project in Google Cloud Console
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Use your client ID and secret with the provided OAuth flow
5. This will generate tokens for your application

### Option 3: Integration with Frontend OAuth Flow
The backend supports OAuth code exchange. If you implement a proper OAuth flow in the frontend, use the `/api/v1/email-accounts/connect/gmail/code` endpoint instead of providing tokens directly.

## Files Modified

- `/backend/app/api/user_email_endpoints.py` - Added Pydantic models and updated all email account endpoints
- `/backend/app/services/email_provider_service.py` - Enhanced error logging in `authenticate_gmail_with_token`

## Next Steps

1. **Restart the backend** to apply these fixes:
   ```bash
   pkill -f "python run.py"
   cd backend && python run.py
   ```

2. **Test the Gmail connection** through the frontend
3. **Monitor the logs** to understand any remaining issues
4. If issues persist, provide the backend logs (with sensitive tokens redacted) for further debugging

## Related Documentation

- [Gmail API Documentation](https://developers.google.com/gmail/api/guides)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Email Accounts API Endpoints](#email-accounts-api)
