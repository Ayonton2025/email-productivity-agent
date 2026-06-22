"""
API endpoints for insights and intelligence:
- /insights/risks
- /insights/opportunities
- /insights/deadlines
- /insights/relationships
- /insights/analytics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.user_models import User
from app.core.security import get_current_user
from app.services.decision_intelligence import DecisionIntelligenceService
from app.services.relationship_service import RelationshipService
from app.models.commitment_models import Commitment, Risk, Opportunity
from app.models.contact_models import Contact, Company

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/risks", response_model=List[Dict[str, Any]])
async def get_risks(
    severity: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active risks for the user"""
    try:
        decision_service = DecisionIntelligenceService(db)
        risks = await decision_service.get_active_risks(
            user_id=current_user.id,
            severity=severity
        )
        return [risk.to_dict() for risk in risks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get risks: {str(e)}")


@router.get("/opportunities", response_model=List[Dict[str, Any]])
async def get_opportunities(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active opportunities for the user"""
    try:
        decision_service = DecisionIntelligenceService(db)
        opportunities = await decision_service.get_active_opportunities(
            user_id=current_user.id,
            status=status
        )
        return [opp.to_dict() for opp in opportunities]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get opportunities: {str(e)}")


@router.get("/deadlines", response_model=List[Dict[str, Any]])
async def get_deadlines(
    days_ahead: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming deadlines"""
    try:
        decision_service = DecisionIntelligenceService(db)
        deadlines = await decision_service.get_upcoming_deadlines(
            user_id=current_user.id,
            days_ahead=days_ahead
        )
        return [commitment.to_dict() for commitment in deadlines]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deadlines: {str(e)}")


@router.get("/relationships", response_model=Dict[str, Any])
async def get_relationships(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get relationship intelligence (contacts and companies)"""
    try:
        relationship_service = RelationshipService(db)
        
        # Get companies
        companies = await relationship_service.get_companies(
            user_id=current_user.id,
            status=status
        )
        
        # Get top contacts by relationship score
        from sqlalchemy import select, desc
        contacts_result = await db.execute(
            select(Contact).where(
                Contact.user_id == current_user.id
            ).order_by(desc(Contact.relationship_score)).limit(50)
        )
        top_contacts = list(contacts_result.scalars().all())
        
        return {
            "companies": [c.to_dict() for c in companies],
            "top_contacts": [c.to_dict() for c in top_contacts],
            "total_companies": len(companies),
            "total_contacts": len(top_contacts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get relationships: {str(e)}")


@router.get("/relationships/heatmap", response_model=Dict[str, Any])
async def relationship_heatmap(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        from sqlalchemy import select
        result = await db.execute(select(Contact).where(Contact.user_id == current_user.id).limit(100))
        contacts = list(result.scalars().all())
        cells = [
            {
                "contact_id": c.id,
                "email": c.email,
                "trust_score": float(c.trust_score or 0.0),
                "stress_level": float(c.stress_level or 0.0),
                "loyalty_score": float(c.loyalty_score or 0.0),
            }
            for c in contacts
        ]
        return {"success": True, "cells": cells, "count": len(cells)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build heatmap: {str(e)}")


@router.get("/analytics", response_model=Dict[str, Any])
async def get_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get email analytics and insights"""
    try:
        from sqlalchemy import select, func, and_
        from app.models.database import Email
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Email statistics
        total_emails = await db.execute(
            select(func.count(Email.id)).where(
                and_(
                    Email.user_id == current_user.id,
                    Email.received_at >= cutoff_date
                )
            )
        )
        total_count = total_emails.scalar() or 0
        
        # By category
        category_stats = await db.execute(
            select(Email.ai_category, func.count(Email.id)).where(
                and_(
                    Email.user_id == current_user.id,
                    Email.received_at >= cutoff_date,
                    Email.ai_category.isnot(None)
                )
            ).group_by(Email.ai_category)
        )
        categories = {row[0]: row[1] for row in category_stats.all()}
        
        # By sentiment
        sentiment_stats = await db.execute(
            select(Email.sentiment, func.count(Email.id)).where(
                and_(
                    Email.user_id == current_user.id,
                    Email.received_at >= cutoff_date,
                    Email.sentiment.isnot(None)
                )
            ).group_by(Email.sentiment)
        )
        sentiments = {row[0]: row[1] for row in sentiment_stats.all()}
        
        # Commitments
        commitments_count = await db.execute(
            select(func.count(Commitment.id)).where(
                and_(
                    Commitment.user_id == current_user.id,
                    Commitment.status.in_(["pending", "in_progress"])
                )
            )
        )
        active_commitments = commitments_count.scalar() or 0
        
        # Risks
        risks_count = await db.execute(
            select(func.count(Risk.id)).where(
                and_(
                    Risk.user_id == current_user.id,
                    Risk.status == "open"
                )
            )
        )
        active_risks = risks_count.scalar() or 0
        
        # Opportunities
        opportunities_count = await db.execute(
            select(func.count(Opportunity.id)).where(
                and_(
                    Opportunity.user_id == current_user.id,
                    Opportunity.status.in_(["new", "qualified", "in_progress"])
                )
            )
        )
        active_opportunities = opportunities_count.scalar() or 0
        
        # Contacts
        contacts_count = await db.execute(
            select(func.count(Contact.id)).where(
                Contact.user_id == current_user.id
            )
        )
        total_contacts = contacts_count.scalar() or 0
        
        # Companies
        companies_count = await db.execute(
            select(func.count(Company.id)).where(
                Company.user_id == current_user.id
            )
        )
        total_companies = companies_count.scalar() or 0
        
        return {
            "period_days": days,
            "email_statistics": {
                "total_emails": total_count,
                "by_category": categories,
                "by_sentiment": sentiments
            },
            "intelligence": {
                "active_commitments": active_commitments,
                "active_risks": active_risks,
                "active_opportunities": active_opportunities
            },
            "relationships": {
                "total_contacts": total_contacts,
                "total_companies": total_companies
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/contacts/{contact_id}", response_model=Dict[str, Any])
async def get_contact_details(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a contact"""
    try:
        from sqlalchemy import select, and_
        from app.models.contact_models import ContactInteraction
        
        # Get contact
        result = await db.execute(
            select(Contact).where(
                and_(Contact.id == contact_id, Contact.user_id == current_user.id)
            )
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Get recent interactions
        interactions_result = await db.execute(
            select(ContactInteraction).where(
                ContactInteraction.contact_id == contact_id
            ).order_by(ContactInteraction.interaction_date.desc()).limit(20)
        )
        interactions = list(interactions_result.scalars().all())
        
        return {
            "contact": contact.to_dict(),
            "recent_interactions": [i.to_dict() for i in interactions]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contact details: {str(e)}")


@router.get("/companies/{company_id}", response_model=Dict[str, Any])
async def get_company_details(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a company"""
    try:
        from sqlalchemy import select, and_
        
        # Get company
        result = await db.execute(
            select(Company).where(
                and_(Company.id == company_id, Company.user_id == current_user.id)
            )
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get contacts for this company
        relationship_service = RelationshipService(db)
        contacts = await relationship_service.get_contacts_by_company(
            user_id=current_user.id,
            company_id=company_id
        )
        
        return {
            "company": company.to_dict(),
            "contacts": [c.to_dict() for c in contacts]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get company details: {str(e)}")


@router.get("/forecast", response_model=Dict[str, Any])
async def forecast_business_insights(
    horizon_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Predictive business insights (MVP heuristic forecast).
    """
    try:
        from sqlalchemy import func, select
        open_risks_result = await db.execute(
            select(func.count(Risk.id)).where(Risk.user_id == current_user.id, Risk.status == "open")
        )
        open_opps_result = await db.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.user_id == current_user.id,
                Opportunity.status.in_(["new", "qualified", "in_progress"]),
            )
        )
        open_risks = int(open_risks_result.scalar() or 0)
        open_opportunities = int(open_opps_result.scalar() or 0)

        revenue_risk_index = min(100, open_risks * 8)
        growth_index = min(100, open_opportunities * 9)
        summary = "Stable"
        if revenue_risk_index - growth_index >= 20:
            summary = "Risk-heavy outlook"
        elif growth_index - revenue_risk_index >= 20:
            summary = "Growth-heavy outlook"

        return {
            "success": True,
            "horizon_days": horizon_days,
            "summary": summary,
            "indices": {
                "revenue_risk_index": revenue_risk_index,
                "growth_opportunity_index": growth_index,
            },
            "drivers": {
                "open_risks": open_risks,
                "open_opportunities": open_opportunities,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to forecast insights: {str(e)}")
