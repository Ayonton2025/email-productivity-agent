"""
Relationship memory timeline endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import get_db
from app.models.timeline_models import RelationshipTimelineEvent
from app.models.user_models import User

router = APIRouter(prefix="/timeline", tags=["timeline"])


class TimelineCreateRequest(BaseModel):
    contact_id: Optional[str] = None
    email_id: Optional[str] = None
    event_type: str
    title: str
    summary: Optional[str] = None


@router.post("/events", response_model=Dict[str, Any])
async def create_timeline_event(
    body: TimelineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = RelationshipTimelineEvent(
        user_id=current_user.id,
        contact_id=body.contact_id,
        email_id=body.email_id,
        event_type=body.event_type,
        title=body.title,
        summary=body.summary,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec.to_dict()


@router.get("/{contact_id}", response_model=List[Dict[str, Any]])
async def get_contact_timeline(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RelationshipTimelineEvent)
        .where(and_(RelationshipTimelineEvent.user_id == current_user.id, RelationshipTimelineEvent.contact_id == contact_id))
        .order_by(desc(RelationshipTimelineEvent.occurred_at))
    )
    return [x.to_dict() for x in result.scalars().all()]
