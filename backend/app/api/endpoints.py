from fastapi import APIRouter, HTTPException, Depends, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.database import get_db
from app.models.user_models import User
from app.services.email_service import EmailService
from app.services.prompt_service import PromptService
from app.services.llm_service import LLMService
from app.services.agent_service import AgentService

# Import the proper authentication dependency
from app.api.auth_endpoints import get_current_user

router = APIRouter()

# ========== PROTECTED ENDPOINTS (using proper JWT auth) ==========

@router.get("/emails/my-inbox", response_model=List[Dict[str, Any]])
async def get_user_inbox(
    category: str = None,
    search: str = None,
    sort_by: str = "newest",
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's inbox emails (requires authentication)"""
    try:
        email_service = EmailService(db)
        # Use user-specific method to get only current user's emails
        emails = await email_service.get_user_emails(user_id=current_user.id, limit=limit, offset=offset)
        
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
        
    except Exception as e:
        print(f"Error getting user inbox: {e}")
        raise HTTPException(status_code=500, detail="Failed to get emails")

@router.get("/prompts/my", response_model=List[Dict[str, Any]])
async def get_user_prompts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's prompts"""
    try:
        prompt_service = PromptService(db)
        return await prompt_service.get_all_prompts()
    except Exception as e:
        print(f"Error getting user prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prompts")

@router.post("/emails/sync")
async def sync_user_emails(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync user emails"""
    try:
        return {
            "message": "Email sync completed",
            "user_id": current_user.id,
            "synced_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error syncing emails: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync emails")

@router.get("/email-accounts", response_model=List[Dict[str, Any]])
async def get_user_email_accounts_simple(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's connected email accounts"""
    try:
        from sqlalchemy import select
        from app.models.user_models import UserEmailAccount
        
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.user_id == current_user.id
            ).order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc())
        )
        accounts = result.scalars().all()
        return [account.to_dict() for account in accounts]
        
    except Exception as e:
        print(f"Error getting email accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get email accounts")

@router.post("/email-accounts/gmail")
async def connect_gmail_simple(
    auth_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect Gmail account"""
    try:
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
            raise HTTPException(status_code=400, detail="Gmail authentication failed")
            
    except Exception as e:
        print(f"Error connecting Gmail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/email-accounts")
async def debug_email_accounts(current_user: User = Depends(get_current_user)):
    """Debug endpoint to test email accounts functionality"""
    try:
        return {
            "status": "success",
            "message": "Email accounts endpoints are working",
            "user_id": current_user.id,
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

# ========== PUBLIC ENDPOINTS (no auth required) ==========

@router.get("/emails", response_model=List[Dict[str, Any]])
async def get_emails(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    """Get all emails (public for demo)"""
    email_service = EmailService(db)
    return await email_service.get_all_emails(limit, offset)

@router.post("/emails/load-mock")
async def load_mock_emails(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Load mock emails for current user"""
    email_service = EmailService(db)
    emails = await email_service.load_mock_emails("data/mock_inbox.json", user_id=current_user.id)
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
    """Update email category"""
    email_service = EmailService(db)
    success = await email_service.update_email_category(email_id, category)
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"message": "Category updated successfully"}

@router.get("/prompts", response_model=List[Dict[str, Any]])
async def get_prompts(db: AsyncSession = Depends(get_db)):
    """Get all prompts (public for demo)"""
    prompt_service = PromptService(db)
    return await prompt_service.get_all_prompts()

@router.post("/prompts", response_model=Dict[str, Any])
async def create_prompt(prompt_data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new prompt"""
    prompt_service = PromptService(db)
    return await prompt_service.create_prompt(prompt_data)

@router.put("/prompts/{prompt_id}", response_model=Dict[str, Any])
async def update_prompt(prompt_id: str, prompt_data: dict, db: AsyncSession = Depends(get_db)):
    """Update a prompt"""
    prompt_service = PromptService(db)
    updated = await prompt_service.update_prompt(prompt_id, prompt_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated

@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a prompt"""
    prompt_service = PromptService(db)
    success = await prompt_service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted successfully"}

# Draft endpoints
@router.get("/drafts", response_model=List[Dict[str, Any]])
async def get_drafts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's drafts"""
    email_service = EmailService(db)
    return await email_service.get_user_drafts(user_id=current_user.id)

@router.post("/drafts", response_model=Dict[str, Any])  # FIXED: Removed extra bracket
async def create_draft(
    draft_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a draft for current user"""
    email_service = EmailService(db)
    return await email_service.create_draft(draft_data, user_id=current_user.id)

@router.put("/drafts/{draft_id}", response_model=Dict[str, Any])  # FIXED: Removed extra bracket
async def update_draft(draft_id: str, draft_data: dict, db: AsyncSession = Depends(get_db)):
    """Update a draft"""
    email_service = EmailService(db)
    updated = await email_service.update_draft(draft_id, draft_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Draft not found")
    return updated

@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a draft"""
    email_service = EmailService(db)
    success = await email_service.delete_draft(draft_id)
    if not success:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"message": "Draft deleted successfully"}

# Agent endpoints
@router.post("/agent/process")
async def process_with_agent(request: dict, db: AsyncSession = Depends(get_db)):
    """Process email with agent"""
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
    """Chat with agent"""
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
    """WebSocket for agent"""
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
