"""
Offline sync queue endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import get_db
from app.models.offline_models import OfflineSyncQueueItem
from app.models.user_models import User

router = APIRouter(prefix="/offline", tags=["offline"])


class OfflineQueueRequest(BaseModel):
    action: str
    payload: Dict[str, Any] = {}


@router.post("/sync-queue", response_model=Dict[str, Any])
async def queue_offline_action(
    body: OfflineQueueRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = OfflineSyncQueueItem(user_id=current_user.id, action=body.action, payload=body.payload, status="queued")
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec.to_dict()


@router.post("/sync-queue/process", response_model=Dict[str, Any])
async def process_offline_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OfflineSyncQueueItem).where(
            and_(OfflineSyncQueueItem.user_id == current_user.id, OfflineSyncQueueItem.status == "queued")
        )
    )
    items = list(result.scalars().all())
    for item in items:
        item.status = "synced"
        item.synced_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "processed": len(items)}


@router.get("/sync-queue", response_model=List[Dict[str, Any]])
async def list_offline_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OfflineSyncQueueItem).where(OfflineSyncQueueItem.user_id == current_user.id))
    return [x.to_dict() for x in result.scalars().all()]
