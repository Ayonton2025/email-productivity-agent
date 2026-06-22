"""
Knowledge base endpoints (RAG-ready).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.database import Email, get_db
from app.models.knowledge_models import KnowledgeEntry
from app.models.user_models import User
from app.services.advanced_features_service import AdvancedFeaturesService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeIngestRequest(BaseModel):
    email_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = []


@router.post("/ingest", response_model=Dict[str, Any])
async def ingest_knowledge(
    body: KnowledgeIngestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    title = body.title or "Knowledge entry"
    content = body.content or ""
    if body.email_id:
        result = await db.execute(select(Email).where(and_(Email.id == body.email_id, Email.user_id == current_user.id)))
        email = result.scalar_one_or_none()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        title = email.subject or title
        content = email.body_text or email.body_html or ""

    entry = KnowledgeEntry(
        user_id=current_user.id,
        email_id=body.email_id,
        title=title,
        content=content,
        embedding=AdvancedFeaturesService.pseudo_embedding(content),
        source="email" if body.email_id else "manual",
        tags=body.tags,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"success": True, "entry": entry.to_dict()}


@router.get("/search", response_model=Dict[str, Any])
async def search_knowledge(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query_embedding = AdvancedFeaturesService.pseudo_embedding(q)
    result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.user_id == current_user.id)
        .order_by(desc(KnowledgeEntry.created_at))
        .limit(200)
    )
    rows = list(result.scalars().all())
    scored = []
    for row in rows:
        score = AdvancedFeaturesService.cosine_like(query_embedding, row.embedding or [])
        scored.append({"score": round(score, 4), "entry": row.to_dict()})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"success": True, "query": q, "results": scored[:limit]}
