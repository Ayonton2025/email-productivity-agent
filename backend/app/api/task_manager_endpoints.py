"""
Task manager endpoints generated from email actions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import get_db
from app.models.task_models import EmailTask
from app.models.user_models import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    email_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    lane: str = "backlog"
    due_at: Optional[str] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    lane: Optional[str] = None
    priority: Optional[str] = None
    due_at: Optional[str] = None
    slack_notified: Optional[bool] = None


@router.get("/", response_model=List[Dict[str, Any]])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailTask).where(EmailTask.user_id == current_user.id))
    return [x.to_dict() for x in result.scalars().all()]


@router.post("/", response_model=Dict[str, Any])
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    due = datetime.fromisoformat(body.due_at) if body.due_at else None
    rec = EmailTask(
        user_id=current_user.id,
        email_id=body.email_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        lane=body.lane,
        due_at=due,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec.to_dict()


@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task(
    task_id: str,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailTask).where(and_(EmailTask.id == task_id, EmailTask.user_id == current_user.id)))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.status is not None:
        rec.status = body.status
    if body.lane is not None:
        rec.lane = body.lane
    if body.priority is not None:
        rec.priority = body.priority
    if body.slack_notified is not None:
        rec.slack_notified = body.slack_notified
    if body.due_at is not None:
        rec.due_at = datetime.fromisoformat(body.due_at)
    await db.commit()
    await db.refresh(rec)
    return rec.to_dict()
