"""
Voice assistant endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, EmailDraft, get_db
from app.models.user_models import User

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceReadRequest(BaseModel):
    email_id: str


class VoiceReplyRequest(BaseModel):
    email_id: str
    spoken_text: str


@router.post("/read-email", response_model=Dict[str, Any])
async def read_email(
    body: VoiceReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Email).where(and_(Email.id == body.email_id, Email.user_id == current_user.id)))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    spoken = f"From {email.sender}. Subject {email.subject or 'No subject'}. {email.body_text or ''}"
    return {"success": True, "transcript": spoken[:1200], "tts_hint": "Use Google TTS or browser speech synthesis"}


@router.post("/reply", response_model=Dict[str, Any])
async def voice_reply(
    body: VoiceReplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Email).where(and_(Email.id == body.email_id, Email.user_id == current_user.id)))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    draft = EmailDraft(
        user_id=current_user.id,
        subject=f"Re: {email.subject or ''}".strip(),
        body=body.spoken_text,
        recipient=email.sender,
        context_email_id=email.id,
        draft_metadata={"source": "voice_assistant", "stt_provider": "openai_whisper_or_hf"},
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return {"success": True, "draft_id": draft.id}
