"""Agent endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AgentChatRequest, AgentProcessRequest
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user_models import User
from app.services.email_service import EmailService
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService

router = APIRouter()
# Preserve the established log category for compatibility with operational filters.
logger = get_logger("app.api.endpoints")


@router.post("/agent/process")
async def process_with_agent(
    request: AgentProcessRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Process email with agent using system prompts"""
    try:
        email_service = EmailService(db)
        llm_service = LLMService()
        prompt_service = PromptService(db)

        email_id = request.email_id
        prompt_type = request.prompt_type
        custom_prompt = request.custom_prompt
        system_prompt_name = request.system_prompt

        # ✅ REMOVED: Don't automatically ensure user has emails here
        # await email_service.ensure_user_has_emails(current_user.id)

        # Get email with user_id filter for security
        email = await email_service.get_email_by_id(email_id, current_user.id)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        # Get system prompt if specified
        system_prompt_text = None
        if system_prompt_name:
            system_prompt = await prompt_service.get_system_prompt(system_prompt_name)
            if system_prompt:
                system_prompt_text = system_prompt.template
                logger.info(f"🔧 [agent/process] Using system prompt: {system_prompt_name}")
            else:
                logger.error(f"⚠️ [agent/process] System prompt not found: {system_prompt_name}")

        if custom_prompt:
            prompt_text = custom_prompt
        else:
            prompt = await prompt_service.get_active_prompt(prompt_type)
            if not prompt:
                raise HTTPException(status_code=404, detail=f"No active prompt found for {prompt_type}")
            prompt_text = prompt.template

        email_content = f"From: {email['sender']}\nSubject: {email['subject']}\nBody: {email['body']}"

        # Pass system prompt to LLM service
        result = await llm_service.process_prompt(prompt_text, email_content, system_prompt_text)

        return {
            "email_id": email_id,
            "prompt_type": prompt_type,
            "system_prompt_used": system_prompt_name if system_prompt_name else None,
            "result": result,
            "used_custom_prompt": custom_prompt is not None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [process_with_agent] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")


@router.post("/agent/chat")
async def chat_with_agent(request: AgentChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat with agent"""
    message = request.message

    llm_service = LLMService()
    response = await llm_service.process_prompt(
        "You are a helpful email productivity assistant. Respond to the user's question helpfully and concisely.",
        message,
    )

    return {"response": response, "timestamp": datetime.utcnow().isoformat()}


@router.get("/agent/status")
async def get_agent_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compatibility status endpoint used by frontend agentApi.getAgentStatus."""
    email_service = EmailService(db)
    total_emails = len(await email_service.get_user_emails(user_id=current_user.id, limit=1000, offset=0))
    return {
        "status": "ready",
        "user_id": current_user.id,
        "capabilities": ["chat", "process_email", "draft_generation"],
        "email_count": total_emails,
        "timestamp": datetime.utcnow().isoformat(),
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
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)
