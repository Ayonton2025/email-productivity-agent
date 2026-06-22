"""
AI ethics and bias moderation endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user_models import User
from app.services.advanced_features_service import AdvancedFeaturesService

router = APIRouter(prefix="/ethics", tags=["ethics"])


class ModerateReplyRequest(BaseModel):
    reply: str


@router.post("/moderate-reply", response_model=Dict[str, Any])
async def moderate_reply(
    body: ModerateReplyRequest,
    current_user: User = Depends(get_current_user),
):
    del current_user
    return {"success": True, **AdvancedFeaturesService.moderate_reply(body.reply)}
