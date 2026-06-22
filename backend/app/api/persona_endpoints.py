"""
Persona profile endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import get_db
from app.models.persona_models import PersonaProfile
from app.models.user_models import User

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaCreate(BaseModel):
    name: str
    tone: str = "professional"
    style: str = "clear"
    signature: Optional[str] = None
    emoji_level: int = 0
    is_default: bool = False


@router.get("/", response_model=List[Dict[str, Any]])
async def list_personas(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PersonaProfile).where(PersonaProfile.user_id == current_user.id))
    return [x.to_dict() for x in result.scalars().all()]


@router.post("/", response_model=Dict[str, Any])
async def create_persona(
    body: PersonaCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.is_default:
        reset = await db.execute(select(PersonaProfile).where(PersonaProfile.user_id == current_user.id))
        for p in reset.scalars().all():
            p.is_default = False
    rec = PersonaProfile(
        user_id=current_user.id,
        name=body.name,
        tone=body.tone,
        style=body.style,
        signature=body.signature,
        emoji_level=max(0, min(5, body.emoji_level)),
        is_default=body.is_default,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec.to_dict()


@router.delete("/{persona_id}", response_model=Dict[str, Any])
async def delete_persona(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PersonaProfile).where(and_(PersonaProfile.id == persona_id, PersonaProfile.user_id == current_user.id))
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Persona not found")
    await db.delete(rec)
    await db.commit()
    return {"success": True}
