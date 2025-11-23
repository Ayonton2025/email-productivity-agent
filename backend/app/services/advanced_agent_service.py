import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.services.enhanced_llm_service import EnhancedLLMService
from app.models.database import Email, EmailDraft

class AdvancedAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = EnhancedLLMService()
    
    async def process_email_intelligently(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email with advanced AI analysis"""
        # Perform comprehensive analysis
        analysis = await self.llm_service.advanced_email_analysis(email_data, "comprehensive_analysis")
        
        # Store or update email in database
        email = await self._store_analyzed_email(email_data, analysis)
        
        return email.to_dict() if email else analysis
    
    async def get_email_insights(self, time_range: str = "week") -> Dict[str, Any]:
        """Get advanced insights across emails"""
        emails = await self._get_emails_by_time_range(time_range)
        
        if not emails:
            return {"insights": [], "summary": "No emails found for analysis"}
        
        # Use AI to generate cross-email insights
        insights = await self.llm_service.advanced_email_analysis(
            {"emails": [email.to_dict() for email in emails]},
            "cross_email_insights"
        )
        
        return {
            "time_range": time_range,
            "emails_analyzed": len(emails),
            "insights": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def generate_contextual_reply(self, email_id: str, tone: str = "professional") -> Dict[str, Any]:
        """Generate reply with full context awareness"""
        email = await self._get_email_by_id(email_id)
        if not email:
            return {"error": "Email not found"}
        
        # Get related emails for context
        related_emails = await self._get_related_emails(email)
        
        # Generate smart reply
        reply = await self.llm_service.generate_smart_reply(
            email.to_dict(),
            tone,
            [e.to_dict() for e in related_emails]
        )
        
        # Store as draft
        draft = EmailDraft(
            subject=reply["subject"],
            body=reply["body"],
            recipient=email.sender,
            context_email_id=email_id,
            tone=tone,
            draft_metadata=reply
        )
        
        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)
        
        return draft.to_dict()
    
    async def analyze_productivity_patterns(self) -> Dict[str, Any]:
        """Analyze user's email productivity patterns"""
        recent_emails = await self._get_emails_by_time_range("month")
        
        analysis_data = {
            "total_emails": len(recent_emails),
            "categories": {},
            "senders": {},
            "response_times": [],
            "busy_periods": []
        }
        
        for email in recent_emails:
            # Categorize by type
            category = email.category or "Uncategorized"
            analysis_data["categories"][category] = analysis_data["categories"].get(category, 0) + 1
            
            # Analyze senders
            sender = email.sender
            analysis_data["senders"][sender] = analysis_data["senders"].get(sender, 0) + 1
        
        return {
            "patterns": analysis_data,
            "recommendations": await self._generate_productivity_recommendations(analysis_data),
            "analysis_date": datetime.utcnow().isoformat()
        }
    
    async def _get_emails_by_time_range(self, time_range: str) -> List[Email]:
        """Get emails from specified time range"""
        if time_range == "day":
            start_date = datetime.utcnow() - timedelta(days=1)
        elif time_range == "week":
            start_date = datetime.utcnow() - timedelta(weeks=1)
        elif time_range == "month":
            start_date = datetime.utcnow() - timedelta(days=30)
        else:
            start_date = datetime.utcnow() - timedelta(days=7)
        
        result = await self.db.execute(
            select(Email).where(Email.timestamp >= start_date).order_by(Email.timestamp.desc())
        )
        return result.scalars().all()
    
    async def _get_email_by_id(self, email_id: str) -> Optional[Email]:
        """Get email by ID"""
        result = await self.db.execute(select(Email).where(Email.id == email_id))
        return result.scalar_one_or_none()
    
    async def _get_related_emails(self, email: Email) -> List[Email]:
        """Get emails related to the given email (same sender, similar subject)"""
        result = await self.db.execute(
            select(Email).where(
                (Email.sender == email.sender) |
                (Email.subject.contains(email.subject.split()[0] if email.subject else ""))
            ).order_by(Email.timestamp.desc()).limit(10)
        )
        return result.scalars().all()
    
    async def _store_analyzed_email(self, email_data: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Email]:
        """Store or update email with analysis results"""
        try:
            # Check if email already exists
            result = await self.db.execute(
                select(Email).where(Email.id == email_data.get('id'))
            )
            existing_email = result.scalar_one_or_none()
            
            if existing_email:
                # Update existing email
                existing_email.category = analysis.get('category', existing_email.category)
                existing_email.priority = analysis.get('priority', existing_email.priority)
                existing_email.summary = analysis.get('summary', existing_email.summary)
                existing_email.action_items = analysis.get('action_items', existing_email.action_items)
                existing_email.email_metadata = {**existing_email.email_metadata, **analysis}
            else:
                # Create new email
                existing_email = Email(
                    id=email_data.get('id'),
                    sender=email_data.get('sender'),
                    subject=email_data.get('subject'),
                    body=email_data.get('body'),
                    timestamp=datetime.fromisoformat(email_data.get('timestamp').replace('Z', '+00:00')),
                    category=analysis.get('category'),
                    priority=analysis.get('priority'),
                    summary=analysis.get('summary'),
                    action_items=analysis.get('action_items', []),
                    email_metadata=analysis
                )
                self.db.add(existing_email)
            
            await self.db.commit()
            await self.db.refresh(existing_email)
            return existing_email
            
        except Exception as e:
            print(f"Error storing analyzed email: {e}")
            await self.db.rollback()
            return None
    
    async def _generate_productivity_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate productivity recommendations based on patterns"""
        recommendations = []
        
        total_emails = patterns["total_emails"]
        categories = patterns["categories"]
        
        # Basic recommendations
        if total_emails > 100:
            recommendations.append("Consider setting up email filters for frequent senders")
        
        if categories.get("Newsletter", 0) > total_emails * 0.3:
            recommendations.append("You have many newsletters. Consider unsubscribing from less relevant ones")
        
        if categories.get("Spam", 0) > 10:
            recommendations.append("Your spam filter might need adjustment")
        
        return recommendations