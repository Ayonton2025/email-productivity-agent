"""
Security and scam detection endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, get_db
from app.models.security_models import EmailSecurityScan
from app.models.user_models import User
from app.services.advanced_features_service import AdvancedFeaturesService

router = APIRouter(prefix="/security", tags=["security"])


class SecurityScanRequest(BaseModel):
    email_id: str


@router.post("/scan-email", response_model=Dict[str, Any])
async def scan_email(
    body: SecurityScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Email).where(and_(Email.id == body.email_id, Email.user_id == current_user.id)))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    scan = AdvancedFeaturesService.score_security(email.sender, email.subject, email.body_text or email.body_html)
    rec = EmailSecurityScan(
        user_id=current_user.id,
        email_id=email.id,
        scam_score=scan["scam_score"],
        phishing_signals=scan["signals"],
        verdict=scan["verdict"],
        rationale="Heuristic fallback scanner. Replace with trained classifier in production.",
        model="heuristic-v1",
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return {"success": True, "scan": rec.to_dict()}
