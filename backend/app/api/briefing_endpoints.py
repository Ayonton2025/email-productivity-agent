"""
Phase 1 Daily Briefing API endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, logger
from app.models.database import get_db
from app.models.user_models import User
from app.services.daily_briefing_service import DailyBriefingService

router = APIRouter(prefix="/briefings", tags=["briefings"])
briefing_service = DailyBriefingService()


class DigestPreferenceUpdateRequest(BaseModel):
    timezone: str = Field(default="UTC", max_length=100)
    send_hour: int = Field(default=6, ge=0, le=23)
    enabled: bool = True


@router.get("/today")
async def get_today_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        briefing = await briefing_service.get_today_briefing(current_user.id, db)
        if not briefing:
            briefing = await briefing_service.generate_daily_briefing(current_user.id, db)
        return {"success": True, "briefing": briefing.to_dict()}
    except Exception as e:
        logger.error("Failed to get today's briefing: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to load daily briefing")


@router.post("/regenerate")
async def regenerate_today_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        pref = await briefing_service.get_or_create_preference(current_user.id, db)
        target_date = datetime.now().date()
        if pref.timezone:
            try:
                from zoneinfo import ZoneInfo

                target_date = datetime.now(ZoneInfo(pref.timezone)).date()
            except Exception:
                pass

        briefing = await briefing_service.generate_daily_briefing(
            user_id=current_user.id,
            session=db,
            target_date=target_date,
            force_regenerate=True,
        )
        return {"success": True, "briefing": briefing.to_dict()}
    except Exception as e:
        logger.error("Failed to regenerate briefing: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to regenerate briefing")


@router.get("/preferences")
async def get_digest_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = await briefing_service.get_or_create_preference(current_user.id, db)
    return {"success": True, "preferences": pref.to_dict()}


@router.put("/preferences")
async def update_digest_preferences(
    request: DigestPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        pref = await briefing_service.get_or_create_preference(current_user.id, db)
        pref.timezone = request.timezone
        pref.send_hour = request.send_hour
        pref.enabled = request.enabled
        await db.flush()
        return {"success": True, "preferences": pref.to_dict()}
    except Exception as e:
        logger.error("Failed to update digest preferences: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to update preferences")
