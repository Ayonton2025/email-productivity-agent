"""
Social cross-posting endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user_models import User

router = APIRouter(prefix="/social", tags=["social"])


class CrossPostRequest(BaseModel):
    source_email_id: str
    platform: str  # linkedin, x
    draft_post: str
    require_approval: bool = True


@router.post("/cross-post", response_model=Dict[str, Any])
async def cross_post(
    body: CrossPostRequest,
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "source_email_id": body.source_email_id,
        "platform": body.platform.lower(),
        "approval_required": body.require_approval,
        "message": "Post generated and queued for approval before publish.",
        "preview": body.draft_post[:280],
        "user_id": current_user.id,
    }
