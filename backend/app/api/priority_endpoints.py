"""
Future priority prediction endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, get_db
from app.models.user_models import User
from app.services.advanced_features_service import AdvancedFeaturesService

router = APIRouter(prefix="/priority", tags=["priority"])


class PriorityPredictRequest(BaseModel):
    email_id: str


@router.post("/predict", response_model=Dict[str, Any])
async def predict_future_priority(
    body: PriorityPredictRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Email).where(and_(Email.id == body.email_id, Email.user_id == current_user.id)))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    score = AdvancedFeaturesService.predict_priority(email.sender, email.subject, email.body_text or email.body_html)
    email.future_priority_score = score
    await db.commit()
    await db.refresh(email)
    return {"success": True, "email_id": email.id, "future_priority_score": score}
