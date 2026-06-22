"""
Full-Text Search Endpoints (Elasticsearch)

Provides full-text search across email content with filtering and pagination.
Falls back to database search if Elasticsearch is not available.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.security import get_current_user
from app.models.database import User, Email, get_db
from app.services.elasticsearch_service import elasticsearch_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails/search", tags=["full-text-search"])


@router.get("/full-text", response_model=dict)
async def full_text_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    is_read: Optional[bool] = None,
    is_flagged: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Full-text search across emails with optional filtering.
    
    Uses Elasticsearch if available, falls back to database search.
    
    Query Parameters:
    - q: Search query (required) - searches in subject, sender, recipients, body
    - limit: Results per page (default: 50, max: 500)
    - offset: Pagination offset (default: 0)
    - category: Filter by AI category (work, personal, newsletter, etc.)
    - is_read: Filter by read status (true/false)
    - is_flagged: Filter by flag status (true/false)
    - date_from: Filter emails after this date (ISO format)
    - date_to: Filter emails before this date (ISO format)
    
    Response:
    {
        "results": [
            {
                "email_id": 123,
                "subject": "Meeting Tomorrow",
                "sender": "boss@company.com",
                "received_at": "2024-01-15T10:30:00",
                "ai_category": "work",
                "snippet": "This is a meeting request for tomorrow at 2 PM...",
                "score": 15.5
            }
        ],
        "total": 150,
        "offset": 0,
        "limit": 50,
        "has_more": true,
        "search_engine": "elasticsearch" or "database"
    }
    """
    try:
        filters = {}
        if category:
            filters["category"] = category
        if is_read is not None:
            filters["is_read"] = is_read
        if is_flagged is not None:
            filters["is_flagged"] = is_flagged
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        
        # Try Elasticsearch first if available
        if elasticsearch_service.enabled:
            logger.debug(f"🔍 Searching Elasticsearch for: {q}")
            result = await elasticsearch_service.search(
                user_id=current_user.id,
                query=q,
                limit=limit,
                offset=offset,
                filters=filters
            )
            
            if "error" not in result:
                return {
                    "results": result.get("hits", []),
                    "total": result.get("total", 0),
                    "offset": offset,
                    "limit": limit,
                    "has_more": offset + limit < result.get("total", 0),
                    "search_engine": "elasticsearch"
                }
            
            logger.warning(f"⚠️ Elasticsearch search failed: {result.get('error')}")
        
        # Fallback to database search
        logger.debug(f"🔍 Searching database for: {q}")
        query = select(Email).where(Email.user_id == current_user.id)
        
        # Apply search query (subject, sender, recipients, body)
        search_pattern = f"%{q}%"
        query = query.where(
            (Email.subject.ilike(search_pattern)) |
            (Email.sender.ilike(search_pattern)) |
            (Email.body_text.ilike(search_pattern))
        )
        
        # Apply filters
        if category:
            query = query.where(Email.ai_category == category)
        if is_read is not None:
            query = query.where(Email.is_read == is_read)
        if is_flagged is not None:
            query = query.where(Email.is_flagged == is_flagged)
        
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from)
                query = query.where(Email.received_at >= from_date)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to)
                query = query.where(Email.received_at <= to_date)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")
        
        # Get total count
        count_result = await db.execute(
            select(Email).where(Email.user_id == current_user.id)
        )
        total = len(count_result.scalars().all())
        
        # Order by most recent and apply pagination
        query = query.order_by(Email.received_at.desc()).offset(offset).limit(limit)
        
        result = await db.execute(query)
        emails = result.scalars().all()
        
        # Format results
        results = [
            {
                "email_id": email.id,
                "subject": email.subject,
                "sender": email.sender,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "ai_category": email.ai_category,
                "snippet": (email.body_text[:200] + "...") if email.body_text else "",
                "score": None
            }
            for email in emails
        ]
        
        return {
            "results": results,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total,
            "search_engine": "database"
        }
    
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get("/suggestions", response_model=dict)
async def get_search_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get search suggestions based on partial query.
    
    Suggests subjects, senders, and categories that match the query.
    
    Response:
    {
        "subjects": ["Meeting Tomorrow", "Project Update"],
        "senders": ["boss@company.com", "team@company.com"],
        "categories": ["work", "personal"]
    }
    """
    try:
        search_pattern = f"%{q}%"
        
        # Get matching subjects
        subject_result = await db.execute(
            select(Email.subject)
            .where(
                and_(
                    Email.user_id == current_user.id,
                    Email.subject.ilike(search_pattern)
                )
            )
            .distinct()
            .limit(limit)
        )
        
        subjects = [s for s in subject_result.scalars().all() if s]
        
        # Get matching senders
        sender_result = await db.execute(
            select(Email.sender)
            .where(
                and_(
                    Email.user_id == current_user.id,
                    Email.sender.ilike(search_pattern)
                )
            )
            .distinct()
            .limit(limit)
        )
        
        senders = [s for s in sender_result.scalars().all() if s]
        
        # Get matching categories
        category_result = await db.execute(
            select(Email.ai_category)
            .where(
                and_(
                    Email.user_id == current_user.id,
                    Email.ai_category.ilike(search_pattern)
                )
            )
            .distinct()
            .limit(limit)
        )
        
        categories = [c for c in category_result.scalars().all() if c]
        
        return {
            "subjects": subjects,
            "senders": senders,
            "categories": categories
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suggestions"
        )


@router.get("/advanced", response_model=dict)
async def advanced_search(
    keywords: str = Query(..., description="Space-separated keywords"),
    search_fields: str = Query(
        "subject,sender,body",
        description="Comma-separated fields to search (subject, sender, body, all)"
    ),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    from_address: Optional[str] = None,
    category: Optional[str] = None,
    has_attachments: Optional[bool] = None,
    is_unread_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Advanced search with multiple criteria.
    
    Query Parameters:
    - keywords: Space-separated search terms
    - search_fields: Which fields to search (subject, sender, body, all)
    - date_from/date_to: Date range in ISO format
    - from_address: Filter by sender email
    - category: Filter by AI category
    - has_attachments: Filter emails with attachments (true/false)
    - is_unread_only: Only return unread emails
    - limit: Results per page
    - offset: Pagination offset
    
    Response: Same format as full-text search
    """
    try:
        query = select(Email).where(Email.user_id == current_user.id)
        
        # Parse search fields
        fields = [f.strip() for f in search_fields.split(",")]
        search_pattern = f"%{keywords}%"
        
        # Build field conditions
        field_conditions = []
        if "all" in fields or "subject" in fields:
            field_conditions.append(Email.subject.ilike(search_pattern))
        if "all" in fields or "sender" in fields:
            field_conditions.append(Email.sender.ilike(search_pattern))
        if "all" in fields or "body" in fields:
            field_conditions.append(Email.body_text.ilike(search_pattern))
        
        if field_conditions:
            from sqlalchemy import or_
            query = query.where(or_(*field_conditions))
        
        # Apply filters
        if from_address:
            query = query.where(Email.sender.ilike(f"%{from_address}%"))
        
        if category:
            query = query.where(Email.ai_category == category)
        
        if is_unread_only:
            query = query.where(Email.is_read == False)
        
        if has_attachments is not None:
            if has_attachments:
                query = query.where(Email.attachments != None)
            else:
                query = query.where((Email.attachments == None) | (Email.attachments == []))
        
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from)
                query = query.where(Email.received_at >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to)
                query = query.where(Email.received_at <= to_date)
            except ValueError:
                pass
        
        # Get total
        count_result = await db.execute(query)
        total = len(count_result.scalars().all())
        
        # Paginate
        query = query.order_by(Email.received_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        emails = result.scalars().all()
        
        results = [
            {
                "email_id": email.id,
                "subject": email.subject,
                "sender": email.sender,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "ai_category": email.ai_category,
                "snippet": (email.body_text[:200] + "...") if email.body_text else "",
                "score": None
            }
            for email in emails
        ]
        
        return {
            "results": results,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total,
            "search_engine": "database"
        }
    
    except Exception as e:
        logger.error(f"❌ Advanced search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Advanced search failed"
        )
