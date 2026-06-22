"""
API endpoints for agent management:
- CRUD operations for agents
- Agent activity tracking
- Agent memory management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.models.database import get_db
from app.models.database import Email, EmailDraft
from app.models.user_models import User
from app.core.security import get_current_user
from app.models.agent_models import Agent, AgentMemory, AgentActivity
from sqlalchemy import select, and_, desc

router = APIRouter(prefix="/agents", tags=["agents"])


# Pydantic models
class AgentCreate(BaseModel):
    name: str
    agent_type: str
    description: Optional[str] = None
    system_prompt: str
    instructions: Optional[str] = None
    capabilities: List[str] = []
    subscribe_to_categories: List[str] = []
    subscribe_to_senders: List[str] = []
    subscribe_to_keywords: List[str] = []
    auto_draft_replies: bool = False
    require_approval: bool = True
    strategy_prompt: Optional[str] = None
    approval_threshold: int = 75
    escalation_rules: Dict[str, Any] = {}
    memory_enabled: bool = True
    context_window: int = 10
    tags: List[str] = []


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    instructions: Optional[str] = None
    capabilities: Optional[List[str]] = None
    subscribe_to_categories: Optional[List[str]] = None
    subscribe_to_senders: Optional[List[str]] = None
    subscribe_to_keywords: Optional[List[str]] = None
    auto_draft_replies: Optional[bool] = None
    require_approval: Optional[bool] = None
    strategy_prompt: Optional[str] = None
    approval_threshold: Optional[int] = None
    escalation_rules: Optional[Dict[str, Any]] = None
    memory_enabled: Optional[bool] = None
    context_window: Optional[int] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


@router.get("/", response_model=List[Dict[str, Any]])
async def get_agents(
    agent_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all agents for the user"""
    try:
        query = select(Agent).where(Agent.user_id == current_user.id)
        if agent_type:
            query = query.where(Agent.agent_type == agent_type)
        query = query.order_by(desc(Agent.created_at))
        
        result = await db.execute(query)
        agents = list(result.scalars().all())
        return [a.to_dict() for a in agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents: {str(e)}")


@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific agent"""
    try:
        result = await db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.user_id == current_user.id)
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent"""
    try:
        agent = Agent(
            user_id=current_user.id,
            name=agent_data.name,
            agent_type=agent_data.agent_type,
            description=agent_data.description,
            system_prompt=agent_data.system_prompt,
            instructions=agent_data.instructions,
            capabilities=agent_data.capabilities,
            subscribe_to_categories=agent_data.subscribe_to_categories,
            subscribe_to_senders=agent_data.subscribe_to_senders,
            subscribe_to_keywords=agent_data.subscribe_to_keywords,
            auto_draft_replies=agent_data.auto_draft_replies,
            require_approval=agent_data.require_approval,
            strategy_prompt=agent_data.strategy_prompt,
            approval_threshold=max(0, min(100, int(agent_data.approval_threshold))),
            escalation_rules=agent_data.escalation_rules,
            memory_enabled=agent_data.memory_enabled,
            context_window=agent_data.context_window,
            tags=agent_data.tags
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return agent.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.put("/{agent_id}", response_model=Dict[str, Any])
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an agent"""
    try:
        result = await db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.user_id == current_user.id)
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if agent_data.name is not None:
            agent.name = agent_data.name
        if agent_data.description is not None:
            agent.description = agent_data.description
        if agent_data.system_prompt is not None:
            agent.system_prompt = agent_data.system_prompt
        if agent_data.instructions is not None:
            agent.instructions = agent_data.instructions
        if agent_data.capabilities is not None:
            agent.capabilities = agent_data.capabilities
        if agent_data.subscribe_to_categories is not None:
            agent.subscribe_to_categories = agent_data.subscribe_to_categories
        if agent_data.subscribe_to_senders is not None:
            agent.subscribe_to_senders = agent_data.subscribe_to_senders
        if agent_data.subscribe_to_keywords is not None:
            agent.subscribe_to_keywords = agent_data.subscribe_to_keywords
        if agent_data.auto_draft_replies is not None:
            agent.auto_draft_replies = agent_data.auto_draft_replies
        if agent_data.require_approval is not None:
            agent.require_approval = agent_data.require_approval
        if agent_data.strategy_prompt is not None:
            agent.strategy_prompt = agent_data.strategy_prompt
        if agent_data.approval_threshold is not None:
            agent.approval_threshold = max(0, min(100, int(agent_data.approval_threshold)))
        if agent_data.escalation_rules is not None:
            agent.escalation_rules = agent_data.escalation_rules
        if agent_data.memory_enabled is not None:
            agent.memory_enabled = agent_data.memory_enabled
        if agent_data.context_window is not None:
            agent.context_window = agent_data.context_window
        if agent_data.is_active is not None:
            agent.is_active = agent_data.is_active
        if agent_data.tags is not None:
            agent.tags = agent_data.tags
        
        await db.commit()
        await db.refresh(agent)
        return agent.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an agent"""
    try:
        result = await db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.user_id == current_user.id)
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        await db.delete(agent)
        await db.commit()
        return {"message": "Agent deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")


@router.get("/{agent_id}/activities", response_model=List[Dict[str, Any]])
async def get_agent_activities(
    agent_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent activity history"""
    try:
        # Verify agent belongs to user
        result = await db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.user_id == current_user.id)
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        activities_result = await db.execute(
            select(AgentActivity).where(
                AgentActivity.agent_id == agent_id
            ).order_by(desc(AgentActivity.created_at)).limit(limit)
        )
        activities = list(activities_result.scalars().all())
        return [a.to_dict() for a in activities]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent activities: {str(e)}")


@router.get("/{agent_id}/memory", response_model=List[Dict[str, Any]])
async def get_agent_memory(
    agent_id: str,
    memory_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent memory"""
    try:
        # Verify agent belongs to user
        result = await db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.user_id == current_user.id)
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        query = select(AgentMemory).where(AgentMemory.agent_id == agent_id)
        if memory_type:
            query = query.where(AgentMemory.memory_type == memory_type)
        query = query.order_by(desc(AgentMemory.importance_score), desc(AgentMemory.created_at)).limit(limit)
        
        memory_result = await db.execute(query)
        memories = list(memory_result.scalars().all())
        return [m.to_dict() for m in memories]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent memory: {str(e)}")


class NegotiateRequest(BaseModel):
    email_id: str
    goal: str = "Aim for at least 10% better commercial terms while remaining polite."
    context: Optional[str] = None
    confidence: int = 80
    auto_send: bool = False


@router.post("/{agent_id}/negotiate", response_model=Dict[str, Any])
async def negotiate_with_agent(
    agent_id: str,
    body: NegotiateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI negotiation proposal endpoint with approval queue integration."""
    try:
        agent_result = await db.execute(
            select(Agent).where(and_(Agent.id == agent_id, Agent.user_id == current_user.id))
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if agent.agent_type != "negotiation":
            raise HTTPException(status_code=400, detail="Agent is not configured as negotiation")

        email_result = await db.execute(
            select(Email).where(and_(Email.id == body.email_id, Email.user_id == current_user.id))
        )
        email = email_result.scalar_one_or_none()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")

        strategy = agent.strategy_prompt or "Negotiate politely, aim for 10% better price."
        proposed_subject = f"Re: {email.subject or 'Proposal discussion'}"
        proposed_body = (
            "Hi,\n\n"
            "Thank you for sharing the proposal.\n\n"
            f"{strategy}\n"
            f"Primary goal: {body.goal}\n\n"
            "Could we improve the current commercial terms by around 10% while preserving delivery quality?\n"
            "If helpful, we can also discuss phased scope options.\n\n"
            f"Best regards,\n{current_user.full_name or current_user.email}"
        )

        confidence = max(0, min(100, int(body.confidence)))
        approval_required = agent.require_approval or (confidence < int(agent.approval_threshold or 75)) or (not body.auto_send)

        draft = EmailDraft(
            user_id=current_user.id,
            subject=proposed_subject,
            body=proposed_body,
            recipient=email.sender,
            context_email_id=email.id,
            draft_metadata={
                "auto_reply": True,
                "approval_status": "pending" if approval_required else "approved",
                "source": "negotiation_agent",
                "agent_id": agent.id,
                "goal": body.goal,
                "context": body.context,
                "confidence": confidence,
            },
        )
        db.add(draft)

        db.add(
            AgentActivity(
                agent_id=agent.id,
                user_id=current_user.id,
                activity_type="negotiation_proposed",
                email_id=email.id,
                action_taken="draft_created",
                action_result="pending_approval" if approval_required else "approved",
                decision_reasoning=f"confidence={confidence}, threshold={agent.approval_threshold}",
                status="pending_approval" if approval_required else "completed",
            )
        )

        await db.commit()
        await db.refresh(draft)
        return {
            "success": True,
            "draft_id": draft.id,
            "approval_required": approval_required,
            "message": "Negotiation draft queued for approval" if approval_required else "Negotiation draft ready",
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to negotiate: {str(e)}")
