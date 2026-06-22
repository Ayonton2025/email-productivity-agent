"""
Email Sync History Endpoints

Provides APIs for retrieving email sync history and statistics.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import User, get_db, SyncHistory
from app.services.sync_history_service import SyncHistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails/sync", tags=["sync-history"])


@router.get("/history", response_model=List[dict])
async def get_sync_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent email sync history for the current user.
    
    Returns:
    - List of sync operations with status, email count, timing, and errors
    
    Query Parameters:
    - limit: Maximum number of records to return (default: 50)
    
    Response:
    {
        "id": "sync-operation-id",
        "provider": "gmail",
        "sync_type": "incremental",
        "status": "completed",
        "emails_processed": 15,
        "started_at": "2024-01-15T10:30:00",
        "completed_at": "2024-01-15T10:31:00",
        "duration_seconds": 60,
        "error_message": null
    }
    """
    try:
        sync_service = SyncHistoryService(db)
        sync_records = await sync_service.get_sync_history(current_user.id, limit)
        
        return [
            {
                "id": record.id,
                "sync_type": record.sync_type,
                "status": record.status,
                "emails_processed": len(record.emails_processed or []),
                "started_at": record.started_at.isoformat(),
                "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                "duration_seconds": (
                    (record.completed_at - record.started_at).total_seconds()
                    if record.completed_at
                    else None
                ),
                "error_message": record.error_message,
            }
            for record in sync_records
        ]
    
    except Exception as e:
        logger.error(f"❌ Failed to get sync history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync history"
        )


@router.get("/stats", response_model=dict)
async def get_sync_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get email sync statistics for the current user.
    
    Response:
    {
        "total_syncs": 42,
        "completed_syncs": 40,
        "failed_syncs": 2,
        "success_rate": 95.24,
        "total_emails_synced": 5230,
        "avg_emails_per_sync": 130.75,
        "last_sync_time": "2024-01-15T10:31:00",
        "last_sync_status": "completed"
    }
    """
    try:
        sync_service = SyncHistoryService(db)
        stats = await sync_service.get_sync_stats(current_user.id)
        return stats
    
    except Exception as e:
        logger.error(f"❌ Failed to get sync stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync statistics"
        )


@router.get("/{sync_id}", response_model=dict)
async def get_sync_details(
    sync_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific sync operation.
    
    Path Parameters:
    - sync_id: ID of the sync operation
    
    Response:
    {
        "id": "sync-id",
        "sync_type": "incremental",
        "status": "completed",
        "emails_processed": ["email-id-1", "email-id-2", ...],
        "started_at": "2024-01-15T10:30:00",
        "completed_at": "2024-01-15T10:31:00",
        "error_message": null
    }
    """
    try:
        from sqlalchemy import select
        
        # Get sync record
        result = await db.execute(
            select(SyncHistory).where(SyncHistory.id == sync_id)
        )
        sync_record = result.scalars().first()
        
        if not sync_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync record not found"
            )
        
        # Verify ownership
        if sync_record.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this sync record"
            )
        
        return {
            "id": sync_record.id,
            "sync_type": sync_record.sync_type,
            "status": sync_record.status,
            "emails_processed": sync_record.emails_processed or [],
            "started_at": sync_record.started_at.isoformat(),
            "completed_at": sync_record.completed_at.isoformat() if sync_record.completed_at else None,
            "error_message": sync_record.error_message,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get sync details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync details"
        )
