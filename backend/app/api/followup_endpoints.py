"""
Phase 1 Auto Follow-up API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, logger
from app.models.database import Email, get_db
from app.models.user_models import User
from app.services.follow_up_service import FollowUpService

router = APIRouter(prefix="/followups", tags=["followups"])
followup_service = FollowUpService()


class FollowUpPolicyUpdateRequest(BaseModel):
    enabled: bool = True
    min_delay_hours: int = Field(default=48, ge=1, le=720)
    max_stages: int = Field(default=3, ge=1, le=10)
    auto_send: bool = False
    tone_profile: str = Field(default="professional", max_length=64)


class ScheduleFollowUpRequest(BaseModel):
    delay_hours: Optional[int] = Field(default=None, ge=1, le=720)


@router.get("/policy")
async def get_follow_up_policy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    policy = await followup_service.get_or_create_policy(current_user.id, db)
    return {"success": True, "policy": policy.to_dict()}


@router.put("/policy")
async def update_follow_up_policy(
    request: FollowUpPolicyUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        policy = await followup_service.get_or_create_policy(current_user.id, db)
        policy.enabled = request.enabled
        policy.min_delay_hours = request.min_delay_hours
        policy.max_stages = request.max_stages
        policy.auto_send = request.auto_send
        policy.tone_profile = request.tone_profile
        await db.flush()
        return {"success": True, "policy": policy.to_dict()}
    except Exception as e:
        logger.error("Failed to update follow-up policy: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to update follow-up policy")


@router.post("/{email_id}/schedule")
async def schedule_follow_up(
    email_id: str,
    request: ScheduleFollowUpRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        email = await followup_service.schedule_follow_up(
            user_id=current_user.id,
            email_id=email_id,
            session=db,
            delay_hours=request.delay_hours,
        )
        return {"success": True, "email": email.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to schedule follow-up: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to schedule follow-up")


@router.post("/{email_id}/disable")
async def disable_follow_up(
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    email_result = await db.execute(
        select(Email).where(and_(Email.id == email_id, Email.user_id == current_user.id))
    )
    email = email_result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    email.follow_up_enabled = False
    email.follow_up_scheduled_at = None
    await db.flush()
    return {"success": True, "email": email.to_dict()}


@router.get("/queue")
async def list_follow_up_queue(
    status: str = "pending_approval",
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    queue = await followup_service.list_queue(
        user_id=current_user.id,
        session=db,
        status=status,
        limit=max(1, min(limit, 200)),
    )
    return {"success": True, "items": [item.to_dict() for item in queue]}


@router.post("/queue/{execution_id}/approve")
async def approve_follow_up(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        execution = await followup_service.approve_execution(
            user_id=current_user.id,
            execution_id=execution_id,
            session=db,
        )
        return {"success": True, "item": execution.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to approve follow-up execution: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to approve follow-up")


@router.post("/process-due")
async def process_due_followups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manual trigger for due follow-up processing.
    """
    try:
        stats = await followup_service.process_due_followups(session=db, limit=100)
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error("Failed to process due follow-ups: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to process due follow-ups")

