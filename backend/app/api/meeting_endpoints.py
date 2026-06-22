"""
AI calendar and meeting intelligence endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, get_db
from app.models.meeting_models import MeetingRecord
from app.models.user_models import User
from app.services.advanced_features_service import AdvancedFeaturesService

router = APIRouter(prefix="/meetings", tags=["meetings"])


class MeetingDetectRequest(BaseModel):
    email_id: str


class MeetingCreateRequest(BaseModel):
    email_id: Optional[str] = None
    title: str
    attendees: list[str] = []


@router.post("/detect", response_model=Dict[str, Any])
async def detect_meeting_intent(
    body: MeetingDetectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Email).where(and_(Email.id == body.email_id, Email.user_id == current_user.id))
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    payload = AdvancedFeaturesService.detect_meeting_intent(email.subject, email.body_text or email.body_html)
    return {"success": True, "email_id": email.id, **payload}


@router.post("/propose-slots", response_model=Dict[str, Any])
async def propose_slots(
    body: MeetingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = MeetingRecord(
        user_id=current_user.id,
        email_id=body.email_id,
        title=body.title,
        attendees=body.attendees,
        proposed_slots=AdvancedFeaturesService.propose_slots(),
        agenda="\n".join(AdvancedFeaturesService.build_meeting_agenda(body.title)),
        prep_notes="Review previous thread, blockers, and target outcomes before call.",
        status="proposed",
        confidence=78,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"success": True, "meeting": record.to_dict()}


@router.post("/{meeting_id}/agenda", response_model=Dict[str, Any])
async def regenerate_agenda(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MeetingRecord).where(and_(MeetingRecord.id == meeting_id, MeetingRecord.user_id == current_user.id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    record.agenda = "\n".join(AdvancedFeaturesService.build_meeting_agenda(record.title))
    await db.commit()
    await db.refresh(record)
    return {"success": True, "meeting": record.to_dict()}


@router.post("/{meeting_id}/post-summary", response_model=Dict[str, Any])
async def post_meeting_summary(
    meeting_id: str,
    notes: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MeetingRecord).where(and_(MeetingRecord.id == meeting_id, MeetingRecord.user_id == current_user.id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    record.post_summary = notes or f"Meeting '{record.title}' completed with next steps assigned."
    record.status = "completed"
    await db.commit()
    await db.refresh(record)
    return {"success": True, "meeting": record.to_dict()}
