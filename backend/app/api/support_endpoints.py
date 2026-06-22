"""
Customer support auto-resolver endpoints.
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

router = APIRouter(prefix="/support", tags=["support"])


class AutoResolveRequest(BaseModel):
    email_id: str
    resolution_note: str = "Issue resolved automatically using knowledge base and workflow policy."


@router.post("/auto-resolve", response_model=Dict[str, Any])
async def auto_resolve(
    body: AutoResolveRequest,
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
        body=f"Hello,\n\n{body.resolution_note}\n\nBest regards,\nSupport Team",
        recipient=email.sender,
        context_email_id=email.id,
        draft_metadata={"source": "support_auto_resolver", "approval_status": "pending"},
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return {"success": True, "draft_id": draft.id}
