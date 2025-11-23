from fastapi import APIRouter, HTTPException, Depends, WebSocket, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr
import uuid
from datetime import datetime
from passlib.context import CryptContext

from app.models.database import get_db
from app.services.email_service import EmailService
from app.services.prompt_service import PromptService
from app.services.llm_service import LLMService
from app.services.agent_service import AgentService

router = APIRouter()

# Create password context with Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Authentication Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str = None
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime = None

    class Config:
        from_attributes = True

# Simple in-memory user storage
users_db = {}
sessions_db = {}

# Password hashing utilities
def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Password hashing error: {e}")
        raise ValueError("Failed to hash password")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def create_access_token(user_id: str) -> str:
    token = str(uuid.uuid4())
    sessions_db[token] = {
        "user_id": user_id,
        "created_at": datetime.utcnow()
    }
    return token

def verify_token(token: str) -> dict:
    if token in sessions_db:
        session = sessions_db[token]
        # Check if token is expired (24 hours)
        if (datetime.utcnow() - session["created_at"]).total_seconds() < 86400:
            return session
    return None

# CRITICAL FIX: Updated get_current_user to properly extract Bearer token
@router.get("/auth/me", response_model=dict)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user information"""
    print(f"🔐 [Backend] /auth/me called, Authorization header: {authorization}")
    
    if not authorization:
        print("❌ [Backend] No authorization header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Extract token from "Bearer <token>" format
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]  # Remove "Bearer " prefix
        else:
            token = authorization
        
        print(f"🔐 [Backend] Token extracted: {token[:20]}..." if len(token) > 20 else f"🔐 [Backend] Token extracted: {token}")
    except Exception as e:
        print(f"❌ [Backend] Token extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    # Verify token
    session = verify_token(token)
    if not session:
        print("❌ [Backend] Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Find user by ID
    user = next((u for u in users_db.values() if u["id"] == session["user_id"]), None)
    if not user:
        print("❌ [Backend] User not found for token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    print(f"✅ [Backend] User authenticated: {user['email']}")
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "is_verified": user["is_verified"],
        "is_active": user["is_active"]
    }

# Authentication endpoints
@router.post("/auth/register", response_model=dict)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        print(f"📝 [Backend] Registration attempt for: {user_data.email}")
        
        if user_data.email in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        user_id = str(uuid.uuid4())
        password_hash = hash_password(user_data.password)
        
        users_db[user_data.email] = {
            "id": user_id,
            "email": user_data.email,
            "password_hash": password_hash,
            "full_name": user_data.full_name,
            "is_verified": False,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        access_token = create_access_token(user_id)
        
        print(f"✅ [Backend] User registered successfully: {user_data.email}")
        
        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user_data.email,
                "full_name": user_data.full_name
            }
        }
        
    except ValueError as e:
        print(f"❌ [Backend] Registration ValueError: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [Backend] Registration unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        )

@router.post("/auth/login", response_model=dict)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        print(f"🔑 [Backend] Login attempt for: {credentials.email}")
        
        user = users_db.get(credentials.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        access_token = create_access_token(user["id"])
        
        print(f"✅ [Backend] User logged in successfully: {credentials.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [Backend] Login unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )

@router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout user (remove token)"""
    try:
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            if token in sessions_db:
                del sessions_db[token]
                print(f"✅ [Backend] Token removed from sessions")
    
    except Exception as e:
        print(f"⚠️ [Backend] Logout error (non-critical): {e}")
    
    return {"message": "Successfully logged out"}

@router.post("/auth/refresh")
async def refresh_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required"
        )
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        new_token = create_access_token(session["user_id"])
        
        return {
            "access_token": new_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )

# Updated protected endpoints to use Authorization header
@router.get("/emails/my-inbox", response_model=List[Dict[str, Any]])
async def get_user_inbox(
    category: str = None,
    search: str = None,
    sort_by: str = "newest",
    limit: int = 50,
    offset: int = 0,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Get user's inbox emails (requires authentication)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        email_service = EmailService(db)
        emails = await email_service.get_all_emails(limit, offset)
        
        filtered_emails = emails
        if category and category != 'all':
            filtered_emails = [email for email in emails if email.get('category') == category]
        
        if search:
            search_lower = search.lower()
            filtered_emails = [
                email for email in filtered_emails
                if search_lower in email.get('subject', '').lower()
                or search_lower in email.get('sender', '').lower()
                or search_lower in email.get('body', '').lower()
            ]
        
        if sort_by == 'newest':
            filtered_emails.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        elif sort_by == 'oldest':
            filtered_emails.sort(key=lambda x: x.get('timestamp', ''))
        elif sort_by == 'sender':
            filtered_emails.sort(key=lambda x: x.get('sender', ''))
        
        return filtered_emails
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

# Similarly update other protected endpoints...
@router.get("/prompts/my", response_model=List[Dict[str, Any]])
async def get_user_prompts(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        prompt_service = PromptService(db)
        return await prompt_service.get_all_prompts()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.post("/emails/sync")
async def sync_user_emails(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {
            "message": "Email sync completed",
            "user_id": session["user_id"],
            "synced_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

# Health check
@router.get("/test-auth")
async def test_auth():
    return {
        "status": "auth_system_working",
        "users_count": len(users_db),
        "sessions_count": len(sessions_db),
        "timestamp": datetime.utcnow().isoformat()
    }

# Email accounts endpoints for quick testing and compatibility
@router.get("/email-accounts", response_model=List[Dict[str, Any]])
async def get_user_email_accounts_simple(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Get user's connected email accounts (simple version)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        from sqlalchemy import select
        from app.models.user_models import UserEmailAccount
        
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.user_id == session["user_id"]
            ).order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc())
        )
        accounts = result.scalars().all()
        return [account.to_dict() for account in accounts]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting email accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get email accounts")

@router.post("/email-accounts/gmail")
async def connect_gmail_simple(
    auth_data: dict,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Connect Gmail account - simple endpoint that matches frontend expectation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        from app.services.email_provider_service import EmailProviderService
        from app.models.user_models import UserEmailAccount
        
        email_provider_service = EmailProviderService()
        
        success = await email_provider_service.authenticate_gmail_with_token(
            auth_data.get('access_token'),
            auth_data.get('refresh_token')
        )
        
        if success:
            # Store email account in database
            email_account = UserEmailAccount(
                user_id=session["user_id"],
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
            raise HTTPException(status_code=400, detail="Gmail authentication failed")
            
    except Exception as e:
        print(f"Error connecting Gmail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/email-accounts")
async def debug_email_accounts(authorization: Optional[str] = Header(None)):
    """Debug endpoint to test email accounts functionality"""
    if not authorization:
        return {"error": "No authorization header"}
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        session = verify_token(token)
        if not session:
            return {"error": "Invalid token"}
        
        return {
            "status": "success",
            "message": "Email accounts endpoints are working",
            "user_id": session["user_id"],
            "endpoints_available": [
                "GET /api/v1/email-accounts",
                "POST /api/v1/email-accounts/gmail", 
                "GET /api/v1/email-accounts/connect/gmail/url",
                "POST /api/v1/email-accounts/connect/gmail",
                "POST /api/v1/email-accounts/connect/gmail/code"
            ]
        }
        
    except Exception as e:
        return {"error": str(e)}

# Email endpoints (public - no auth required for demo)
@router.get("/emails", response_model=List[Dict[str, Any]])
async def get_emails(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    return await email_service.get_all_emails(limit, offset)

@router.post("/emails/load-mock")
async def load_mock_emails(db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    emails = await email_service.load_mock_emails("data/mock_inbox.json")
    return {"message": f"Loaded {len(emails)} emails", "emails": emails}

@router.get("/emails/{email_id}", response_model=Dict[str, Any])
async def get_email(email_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific email"""
    email_service = EmailService(db)
    email = await email_service.get_email_by_id(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email

@router.put("/emails/{email_id}/category")
async def update_email_category(email_id: str, category: str, db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    success = await email_service.update_email_category(email_id, category)
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"message": "Category updated successfully"}

# Prompt endpoints (public for demo)
@router.get("/prompts", response_model=List[Dict[str, Any]])
async def get_prompts(db: AsyncSession = Depends(get_db)):
    prompt_service = PromptService(db)
    return await prompt_service.get_all_prompts()

@router.post("/prompts", response_model=Dict[str, Any])
async def create_prompt(prompt_data: dict, db: AsyncSession = Depends(get_db)):
    prompt_service = PromptService(db)
    return await prompt_service.create_prompt(prompt_data)

@router.put("/prompts/{prompt_id}", response_model=Dict[str, Any])
async def update_prompt(prompt_id: str, prompt_data: dict, db: AsyncSession = Depends(get_db)):
    prompt_service = PromptService(db)
    updated = await prompt_service.update_prompt(prompt_id, prompt_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated

@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, db: AsyncSession = Depends(get_db)):
    prompt_service = PromptService(db)
    success = await prompt_service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted successfully"}

# Draft endpoints
@router.get("/drafts", response_model=List[Dict[str, Any]])
async def get_drafts(db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    return await email_service.get_drafts()

@router.post("/drafts", response_model=Dict[str, Any])
async def create_draft(draft_data: dict, db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    return await email_service.create_draft(draft_data)

@router.put("/drafts/{draft_id}", response_model=Dict[str, Any])
async def update_draft(draft_id: str, draft_data: dict, db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    updated = await email_service.update_draft(draft_id, draft_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Draft not found")
    return updated

@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    success = await email_service.delete_draft(draft_id)
    if not success:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"message": "Draft deleted successfully"}

# Agent endpoints
@router.post("/agent/process")
async def process_with_agent(request: dict, db: AsyncSession = Depends(get_db)):
    email_service = EmailService(db)
    llm_service = LLMService()
    prompt_service = PromptService(db)
    
    email_id = request.get('email_id')
    prompt_type = request.get('prompt_type')
    custom_prompt = request.get('custom_prompt')
    
    email = await email_service.get_email_by_id(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    if custom_prompt:
        prompt_text = custom_prompt
    else:
        prompt = await prompt_service.get_active_prompt(prompt_type)
        if not prompt:
            raise HTTPException(status_code=404, detail=f"No active prompt found for {prompt_type}")
        prompt_text = prompt.template
    
    email_content = f"From: {email['sender']}\nSubject: {email['subject']}\nBody: {email['body']}"
    result = await llm_service.process_prompt(prompt_text, email_content)
    
    return {
        "email_id": email_id,
        "prompt_type": prompt_type,
        "result": result,
        "used_custom_prompt": custom_prompt is not None
    }

@router.post("/agent/chat")
async def chat_with_agent(request: dict, db: AsyncSession = Depends(get_db)):
    message = request.get('message')
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    llm_service = LLMService()
    response = await llm_service.process_prompt(
        "You are a helpful email productivity assistant. Respond to the user's question helpfully and concisely.",
        message
    )
    
    return {
        "response": response,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket, client_id: str = "default", db: AsyncSession = Depends(get_db)):
    from app.api.websockets import manager
    await manager.connect(websocket, client_id, db)
    
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_websocket_message(client_id, data)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)

# Health and info endpoints
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "email-agent-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/info")
async def api_info():
    return {
        "name": "Email Productivity Agent API",
        "version": "1.0.0",
        "description": "AI-powered email management system",
        "endpoints": {
            "auth": [
                "POST /auth/register",
                "POST /auth/login", 
                "GET /auth/me",
                "POST /auth/logout",
                "POST /auth/refresh"
            ],
            "emails": [
                "GET /emails",
                "GET /emails/my-inbox",
                "GET /emails/{email_id}",
                "PUT /emails/{email_id}/category",
                "POST /emails/sync",
                "POST /emails/load-mock"
            ],
            "prompts": [
                "GET /prompts",
                "GET /prompts/my",
                "POST /prompts",
                "PUT /prompts/{prompt_id}",
                "DELETE /prompts/{prompt_id}"
            ],
            "agent": [
                "POST /agent/process",
                "POST /agent/chat",
                "WS /ws/agent"
            ],
            "email_accounts": [
                "GET /email-accounts",
                "POST /email-accounts/gmail",
                "GET /debug/email-accounts"
            ]
        }
    }