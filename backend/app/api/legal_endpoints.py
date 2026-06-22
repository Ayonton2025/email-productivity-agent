"""
Legal and contract analyzer endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user_models import User
from app.services.advanced_features_service import AdvancedFeaturesService

router = APIRouter(prefix="/legal", tags=["legal"])


class LegalAnalyzeRequest(BaseModel):
    text: str


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_legal(
    body: LegalAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    del current_user
    result = AdvancedFeaturesService.legal_extract(body.text)
    return {"success": True, "analysis": result}
