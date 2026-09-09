from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.system_models import SystemSetting

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.get("/dismissals/reset")
async def get_dismissal_reset_info(session: AsyncSession = Depends(get_db)):
    """Return the last global dismissal-reset timestamp (if any). Public endpoint."""
    key = "premium_prompt_dismissals_reset_at"
    row = await session.get(SystemSetting, key)
    return {"success": True, "reset_at": (row.value if row else None)}
