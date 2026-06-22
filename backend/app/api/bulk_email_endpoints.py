"""
Bulk Email Operations Endpoints

Handles bulk operations on multiple emails (mark read, flag, delete, categorize).
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.security import get_current_user
from app.models.database import User, Email, get_db
from app.api.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails/bulk", tags=["bulk-operations"])


class BulkMarkReadRequest(BaseModel):
    """Request to mark multiple emails as read/unread"""
    email_ids: List[int]
    is_read: bool


class BulkFlagRequest(BaseModel):
    """Request to flag/unflag multiple emails"""
    email_ids: List[int]
    is_flagged: bool


class BulkCategorizeRequest(BaseModel):
    """Request to bulk categorize emails"""
    email_ids: List[int]
    category: str  # work, personal, newsletter, promotions, etc.


class BulkDeleteRequest(BaseModel):
    """Request to delete emails (mark as deleted)"""
    email_ids: List[int]
    soft_delete: bool = True  # True = mark deleted, False = hard delete


@router.patch("/mark-read", response_model=dict)
async def bulk_mark_read(
    request: BulkMarkReadRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark multiple emails as read or unread.
    
    Request:
    {
        "email_ids": [1, 2, 3],
        "is_read": true
    }
    
    Response:
    {
        "status": "success",
        "updated_count": 3,
        "email_ids": [1, 2, 3]
    }
    """
    try:
        if not request.email_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_ids cannot be empty"
            )
        
        # Verify all emails belong to current user
        result = await db.execute(
            select(Email).where(
                Email.id.in_(request.email_ids),
                Email.user_id == current_user.id
            )
        )
        emails = result.scalars().all()
        
        if len(emails) != len(request.email_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Some emails don't exist or don't belong to you"
            )
        
        # Perform bulk update
        await db.execute(
            update(Email)
            .where(Email.id.in_(request.email_ids))
            .values(is_read=request.is_read)
        )
        await db.commit()
        
        # Broadcast WebSocket event
        for email_id in request.email_ids:
            await connection_manager.broadcast_email_read(
                current_user.id,
                email_id,
                request.is_read
            )
        
        logger.info(f"✅ Bulk marked {len(request.email_ids)} emails as read={request.is_read}")
        
        return {
            "status": "success",
            "updated_count": len(request.email_ids),
            "email_ids": request.email_ids
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bulk mark read failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark emails as read"
        )


@router.patch("/flag", response_model=dict)
async def bulk_flag(
    request: BulkFlagRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Flag or unflag multiple emails.
    
    Request:
    {
        "email_ids": [1, 2, 3],
        "is_flagged": true
    }
    
    Response:
    {
        "status": "success",
        "updated_count": 3,
        "email_ids": [1, 2, 3]
    }
    """
    try:
        if not request.email_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_ids cannot be empty"
            )
        
        # Verify all emails belong to current user
        result = await db.execute(
            select(Email).where(
                Email.id.in_(request.email_ids),
                Email.user_id == current_user.id
            )
        )
        emails = result.scalars().all()
        
        if len(emails) != len(request.email_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Some emails don't exist or don't belong to you"
            )
        
        # Perform bulk update
        await db.execute(
            update(Email)
            .where(Email.id.in_(request.email_ids))
            .values(is_flagged=request.is_flagged)
        )
        await db.commit()
        
        # Broadcast WebSocket event
        for email_id in request.email_ids:
            await connection_manager.broadcast_email_flagged(
                current_user.id,
                email_id,
                request.is_flagged
            )
        
        logger.info(f"✅ Bulk flagged {len(request.email_ids)} emails as flagged={request.is_flagged}")
        
        return {
            "status": "success",
            "updated_count": len(request.email_ids),
            "email_ids": request.email_ids
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bulk flag failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flag emails"
        )


@router.patch("/categorize", response_model=dict)
async def bulk_categorize(
    request: BulkCategorizeRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Apply a category to multiple emails.
    
    Request:
    {
        "email_ids": [1, 2, 3],
        "category": "work"
    }
    
    Response:
    {
        "status": "success",
        "updated_count": 3,
        "category": "work"
    }
    """
    try:
        if not request.email_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_ids cannot be empty"
            )
        
        # Validate category
        valid_categories = ["work", "personal", "newsletter", "promotions", "support", "other"]
        if request.category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )
        
        # Verify all emails belong to current user
        result = await db.execute(
            select(Email).where(
                Email.id.in_(request.email_ids),
                Email.user_id == current_user.id
            )
        )
        emails = result.scalars().all()
        
        if len(emails) != len(request.email_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Some emails don't exist or don't belong to you"
            )
        
        # Perform bulk update
        await db.execute(
            update(Email)
            .where(Email.id.in_(request.email_ids))
            .values(user_category=request.category)
        )
        await db.commit()
        
        logger.info(f"✅ Bulk categorized {len(request.email_ids)} emails as {request.category}")
        
        return {
            "status": "success",
            "updated_count": len(request.email_ids),
            "category": request.category
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bulk categorize failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to categorize emails"
        )


@router.delete("/", response_model=dict)
async def bulk_delete(
    request: BulkDeleteRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple emails.
    
    Request:
    {
        "email_ids": [1, 2, 3],
        "soft_delete": true
    }
    
    Response:
    {
        "status": "success",
        "deleted_count": 3
    }
    """
    try:
        if not request.email_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_ids cannot be empty"
            )
        
        # Verify all emails belong to current user
        result = await db.execute(
            select(Email).where(
                Email.id.in_(request.email_ids),
                Email.user_id == current_user.id
            )
        )
        emails = result.scalars().all()
        
        if len(emails) != len(request.email_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Some emails don't exist or don't belong to you"
            )
        
        if request.soft_delete:
            # Soft delete: mark as deleted but keep in database
            await db.execute(
                update(Email)
                .where(Email.id.in_(request.email_ids))
                .values(is_deleted=True)
            )
            action = "soft deleted"
        else:
            # Hard delete: remove from database
            await db.execute(
                select(Email).where(Email.id.in_(request.email_ids))
            )
            for email in emails:
                await db.delete(email)
            action = "permanently deleted"
        
        await db.commit()
        
        logger.info(f"✅ Bulk {action} {len(request.email_ids)} emails")
        
        return {
            "status": "success",
            "deleted_count": len(request.email_ids)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Bulk delete failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete emails"
        )


@router.get("/statistics", response_model=dict)
async def get_bulk_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics for bulk operations availability.
    
    Response:
    {
        "total_emails": 150,
        "unread_emails": 23,
        "flagged_emails": 5,
        "deletable_emails": 145
    }
    """
    try:
        result = await db.execute(
            select(Email).where(Email.user_id == current_user.id)
        )
        all_emails = result.scalars().all()
        
        unread = sum(1 for e in all_emails if not e.is_read)
        flagged = sum(1 for e in all_emails if e.is_flagged)
        deletable = sum(1 for e in all_emails if not getattr(e, 'is_deleted', False))
        
        return {
            "total_emails": len(all_emails),
            "unread_emails": unread,
            "flagged_emails": flagged,
            "deletable_emails": deletable
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get bulk statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )
