"""Draft endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DraftCreateRequest, DraftUpdateRequest
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user_models import User
from app.services.email_service import EmailService

router = APIRouter()
# Preserve the established log category for compatibility with operational filters.
logger = get_logger("app.api.endpoints")


@router.get("/drafts", response_model=List[Dict[str, Any]])
async def get_drafts(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get user's drafts"""
    email_service = EmailService(db)
    return await email_service.get_user_drafts(user_id=current_user.id)


@router.post("/drafts", response_model=Dict[str, Any])
async def create_draft(
    draft_data: DraftCreateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Create a draft for current user"""
    email_service = EmailService(db)
    return await email_service.create_draft(draft_data.model_dump(mode="json"), user_id=current_user.id)


@router.put("/drafts/{draft_id}", response_model=Dict[str, Any])
async def update_draft(draft_id: str, draft_data: DraftUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update a draft"""
    email_service = EmailService(db)
    updated = await email_service.update_draft(draft_id, draft_data.model_dump(mode="json", exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Draft not found")
    return updated


@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a draft"""
    email_service = EmailService(db)
    success = await email_service.delete_draft(draft_id)
    if not success:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"message": "Draft deleted successfully"}
