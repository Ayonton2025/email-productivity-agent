"""
Inbox API Endpoints

Returns emails from the database for display in the inbox.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import List, Optional
import logging

from app.models.database import get_db, Email
from app.models.user_models import User
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["inbox"])


@router.get("/inbox")
async def get_inbox(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    folder: Optional[str] = "INBOX",
    category: Optional[str] = None,
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get inbox emails for the current user.
    
    Query Parameters:
    - limit: Number of emails to return (1-100, default 50)
    - offset: Pagination offset (default 0)
    - folder: Email folder (default "INBOX")
    - category: Filter by AI category (optional)
    - is_read: Filter by read status (optional)
    """
    try:
        # Build query
        query = select(Email).where(Email.user_id == current_user.id)
        
        if folder:
            query = query.where(Email.folder == folder)
        
        if category:
            query = query.where(Email.ai_category == category)
        
        if is_read is not None:
            query = query.where(Email.is_read == is_read)
        
        # Order by received_at descending (newest first)
        query = query.order_by(desc(Email.received_at))
        
        # Get total count
        count_query = select(Email).where(Email.user_id == current_user.id)
        if folder:
            count_query = count_query.where(Email.folder == folder)
        
        count_result = await db.execute(count_query)
        total_count = len(count_result.scalars().all())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        emails = result.scalars().all()
        
        logger.info(f"📧 Retrieved {len(emails)} emails for user {current_user.id} (total: {total_count})")
        
        return {
            "success": True,
            "data": [email.to_dict() for email in emails],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "count": len(emails)
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching inbox: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch inbox: {str(e)}")


@router.get("/unread")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get count of unread emails for the current user.
    """
    try:
        result = await db.execute(
            select(Email).where(
                and_(
                    Email.user_id == current_user.id,
                    Email.is_read == False
                )
            )
        )
        unread_emails = result.scalars().all()
        
        return {
            "success": True,
            "unread_count": len(unread_emails)
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching unread count: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch unread count: {str(e)}")


@router.get("/{email_id}")
async def get_email(
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific email by ID.
    """
    try:
        result = await db.execute(
            select(Email).where(
                and_(
                    Email.id == email_id,
                    Email.user_id == current_user.id
                )
            )
        )
        email = result.scalar_one_or_none()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Mark as read
        email.is_read = True
        await db.commit()
        
        return {
            "success": True,
            "data": email.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch email: {str(e)}")


@router.get("/search/query")
async def search_emails(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search emails by subject or sender.
    
    Query Parameters:
    - q: Search query (required)
    - limit: Number of results (1-100, default 50)
    """
    try:
        # Search in subject and sender
        search_term = f"%{q}%"
        
        result = await db.execute(
            select(Email).where(
                and_(
                    Email.user_id == current_user.id,
                    (Email.subject.ilike(search_term) | Email.sender.ilike(search_term))
                )
            )
            .order_by(desc(Email.received_at))
            .limit(limit)
        )
        
        emails = result.scalars().all()
        
        logger.info(f"📧 Found {len(emails)} emails matching query '{q}'")
        
        return {
            "success": True,
            "query": q,
            "data": [email.to_dict() for email in emails],
            "count": len(emails)
        }
    
    except Exception as e:
        logger.error(f"❌ Error searching emails: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search emails: {str(e)}")


@router.patch("/{email_id}/read")
async def mark_as_read(
    email_id: str,
    is_read: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark email as read or unread.
    """
    try:
        result = await db.execute(
            select(Email).where(
                and_(
                    Email.id == email_id,
                    Email.user_id == current_user.id
                )
            )
        )
        email = result.scalar_one_or_none()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email.is_read = is_read
        await db.commit()
        
        return {
            "success": True,
            "message": f"Email marked as {'read' if is_read else 'unread'}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update email: {str(e)}")


@router.patch("/{email_id}/flag")
async def toggle_flag(
    email_id: str,
    is_flagged: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Flag or unflag an email.
    """
    try:
        result = await db.execute(
            select(Email).where(
                and_(
                    Email.id == email_id,
                    Email.user_id == current_user.id
                )
            )
        )
        email = result.scalar_one_or_none()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email.is_flagged = is_flagged
        await db.commit()
        
        return {
            "success": True,
            "message": f"Email {'flagged' if is_flagged else 'unflagged'}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update email: {str(e)}")


@router.get("/categories/stats")
async def get_category_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics of emails by AI category.
    """
    try:
        result = await db.execute(
            select(Email).where(Email.user_id == current_user.id)
        )
        all_emails = result.scalars().all()
        
        # Count by category
        categories = {}
        for email in all_emails:
            cat = email.ai_category or "Uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "success": True,
            "data": categories,
            "total": len(all_emails)
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching category stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
