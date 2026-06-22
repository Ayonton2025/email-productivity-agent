"""
Multi-language communication endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user_models import User
from app.services.advanced_features_service import AdvancedFeaturesService

router = APIRouter(prefix="/language", tags=["language"])


class TranslateRequest(BaseModel):
    text: str
    target_language: str


class PreferredLanguageRequest(BaseModel):
    preferred_language: str


@router.post("/translate", response_model=Dict[str, Any])
async def translate_text(
    body: TranslateRequest,
    current_user: User = Depends(get_current_user),
):
    del current_user
    translated = AdvancedFeaturesService.translate_text(body.text, body.target_language)
    return {"success": True, "translated_text": translated, "provider_hint": "DeepL or Google Translate"}


@router.put("/preferred-language", response_model=Dict[str, Any])
async def set_preferred_language(
    body: PreferredLanguageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.preferred_language = body.preferred_language.strip().lower()
    await db.commit()
    await db.refresh(current_user)
    return {"success": True, "preferred_language": current_user.preferred_language}
