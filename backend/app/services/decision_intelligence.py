"""
Decision Intelligence Service

Extracts from emails:
- Deadlines
- Commitments ("I will...", "We agreed...")
- Risks (legal, angry, compliance, payment delays)
- Opportunities (sales leads, partnerships, jobs, funding)
"""

from __future__ import annotations

import asyncio
import re
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.database import Email
from app.models.commitment_models import Commitment, Risk, Opportunity
from app.models.contact_models import Contact, Company
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService


class DecisionIntelligenceService:
    """Service for extracting and managing commitments, risks, and opportunities"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)
    
    async def process_email_for_decisions(self, email: Email) -> Dict[str, Any]:
        """
        Process an email to extract commitments, risks, and opportunities.
        Returns dict with extracted items.
        """
        results = {
            "commitments": [],
            "risks": [],
            "opportunities": []
        }
        
        email_content = (
            f"From: {email.sender}\n"
            f"Subject: {email.subject}\n"
            f"Body: {(email.body_text or email.body_html or '')[:8000]}"
        )
        
        # Extract all in parallel
        tasks = [
            self.extract_commitments(email, email_content),
            self.extract_risks(email, email_content),
            self.extract_opportunities(email, email_content)
        ]
        
        commitments, risks, opportunities = await asyncio.gather(*tasks, return_exceptions=True)
        
        if not isinstance(commitments, Exception):
            results["commitments"] = commitments
        if not isinstance(risks, Exception):
            results["risks"] = risks
        if not isinstance(opportunities, Exception):
            results["opportunities"] = opportunities
        
        return results
    
    async def extract_commitments(
        self,
        email: Email,
        email_content: str
    ) -> List[Dict[str, Any]]:
        """Extract commitments, deadlines, and promises from email"""
        try:
            prompt = f"""Extract all commitments, deadlines, promises, and agreements from this email.
Return JSON array with:
{{
  "title": "brief description",
  "description": "full text or context",
  "type": "deadline/promise/agreement/task/meeting",
  "deadline": "YYYY-MM-DD or null",
  "committed_by": "user/contact/unknown",
  "priority": "high/medium/low",
  "extracted_text": "original text snippet"
}}

Look for phrases like:
- "I will...", "We will...", "I promise...", "We agreed..."
- "Deadline: ...", "Due: ...", "By: ..."
- "Meeting on...", "Call at..."
- Dates and time references

Email:
{email_content}

Return only valid JSON array."""

            response = await self.llm_service.process_prompt(prompt, "")
            
            # Parse response
            commitments_data = self._parse_json_response(response, default=[])
            if not isinstance(commitments_data, list):
                commitments_data = []
            
            commitments = []
            for item in commitments_data:
                if not isinstance(item, dict):
                    continue
                
                # Parse deadline
                deadline = None
                if item.get("deadline"):
                    deadline_str = str(item["deadline"])
                    deadline = self._parse_date(deadline_str)
                
                # Determine if user or contact committed
                committed_by = item.get("committed_by", "unknown")
                is_user_commitment = committed_by.lower() in ["user", "i", "we", "me"]
                
                # Check if overdue
                is_overdue = False
                if deadline and deadline < datetime.utcnow():
                    is_overdue = True
                
                commitment = Commitment(
                    user_id=email.user_id,
                    email_id=email.id,
                    title=item.get("title", "Untitled Commitment"),
                    description=item.get("description"),
                    commitment_type=item.get("type", "task"),
                    committed_by=committed_by,
                    is_user_commitment=is_user_commitment,
                    deadline=deadline,
                    is_overdue=is_overdue,
                    priority=item.get("priority", "medium"),
                    extracted_text=item.get("extracted_text"),
                    confidence_score=0.8,
                    status="pending" if not is_overdue else "missed"
                )
                
                self.db.add(commitment)
                commitments.append(commitment)
            
            await self.db.flush()
            return [c.to_dict() for c in commitments]
            
        except Exception as e:
            print(f"⚠️ [DecisionIntelligence] Failed to extract commitments: {e}")
            return []
    
    async def extract_risks(
        self,
        email: Email,
        email_content: str
    ) -> List[Dict[str, Any]]:
        """Extract risks (legal, compliance, payment delays, angry emails)"""
        try:
            prompt = f"""Identify potential risks in this email. Look for:
- Legal threats or concerns
- Compliance issues
- Payment delays or financial concerns
- Angry or hostile tone
- Data breach mentions
- Contract violations
- Churn indicators

Return JSON array with:
{{
  "title": "risk description",
  "description": "details",
  "type": "legal/compliance/payment_delay/angry/churn/data_breach/contract_violation",
  "severity": "critical/high/medium/low",
  "potential_impact": "description of impact",
  "extracted_text": "original text"
}}

Email:
{email_content}

Return only valid JSON array."""

            response = await self.llm_service.process_prompt(prompt, "")
            
            risks_data = self._parse_json_response(response, default=[])
            if not isinstance(risks_data, list):
                risks_data = []
            
            risks = []
            for item in risks_data:
                if not isinstance(item, dict):
                    continue
                
                # Calculate urgency score based on severity
                severity = item.get("severity", "low")
                urgency_map = {"critical": 90, "high": 70, "medium": 50, "low": 30}
                urgency_score = urgency_map.get(severity, 30)
                
                risk = Risk(
                    user_id=email.user_id,
                    email_id=email.id,
                    title=item.get("title", "Unidentified Risk"),
                    description=item.get("description"),
                    risk_type=item.get("type", "unknown"),
                    severity=severity,
                    potential_impact=item.get("potential_impact"),
                    urgency_score=urgency_score,
                    extracted_text=item.get("extracted_text"),
                    confidence_score=0.75,
                    status="open"
                )
                
                self.db.add(risk)
                risks.append(risk)
            
            await self.db.flush()
            return [r.to_dict() for r in risks]
            
        except Exception as e:
            print(f"⚠️ [DecisionIntelligence] Failed to extract risks: {e}")
            return []
    
    async def extract_opportunities(
        self,
        email: Email,
        email_content: str
    ) -> List[Dict[str, Any]]:
        """Extract opportunities (sales leads, partnerships, jobs, funding)"""
        try:
            prompt = f"""Identify business opportunities in this email. Look for:
- Sales inquiries or interest
- Partnership proposals
- Job opportunities
- Funding/investment interest
- Collaboration offers
- New business leads

Return JSON array with:
{{
  "title": "opportunity description",
  "description": "details",
  "type": "sales_lead/partnership/job/funding/collaboration",
  "estimated_value": number or null,
  "probability": 0-100,
  "lead_temperature": "hot/warm/cold",
  "interest_level": "high/medium/low",
  "extracted_text": "original text"
}}

Email:
{email_content}

Return only valid JSON array."""

            response = await self.llm_service.process_prompt(prompt, "")
            
            opportunities_data = self._parse_json_response(response, default=[])
            if not isinstance(opportunities_data, list):
                opportunities_data = []
            
            opportunities = []
            for item in opportunities_data:
                if not isinstance(item, dict):
                    continue
                
                opportunity = Opportunity(
                    user_id=email.user_id,
                    email_id=email.id,
                    title=item.get("title", "New Opportunity"),
                    description=item.get("description"),
                    opportunity_type=item.get("type", "sales_lead"),
                    estimated_value=item.get("estimated_value"),
                    probability=item.get("probability"),
                    lead_temperature=item.get("lead_temperature", "warm"),
                    interest_level=item.get("interest_level", "medium"),
                    extracted_text=item.get("extracted_text"),
                    confidence_score=0.7,
                    status="new"
                )
                
                self.db.add(opportunity)
                opportunities.append(opportunity)
            
            await self.db.flush()
            return [o.to_dict() for o in opportunities]
            
        except Exception as e:
            print(f"⚠️ [DecisionIntelligence] Failed to extract opportunities: {e}")
            return []
    
    def _parse_json_response(self, response: Any, default: Any = None) -> Any:
        """Safely parse JSON from LLM response"""
        if response is None:
            return default
        
        if isinstance(response, (dict, list)):
            return response
        
        if not isinstance(response, str):
            response = str(response)
        
        # Try to extract JSON from response
        json_match = re.search(r'\[.*\]|\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return default
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # Try relative dates
        date_str_lower = date_str.lower()
        today = datetime.utcnow()
        
        if "today" in date_str_lower:
            return today
        elif "tomorrow" in date_str_lower:
            return today + timedelta(days=1)
        elif "next week" in date_str_lower:
            return today + timedelta(days=7)
        elif "next month" in date_str_lower:
            return today + timedelta(days=30)
        
        return None
    
    async def get_upcoming_deadlines(
        self,
        user_id: str,
        days_ahead: int = 7
    ) -> List[Commitment]:
        """Get upcoming deadlines within specified days"""
        cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        result = await self.db.execute(
            select(Commitment).where(
                and_(
                    Commitment.user_id == user_id,
                    Commitment.deadline.isnot(None),
                    Commitment.deadline <= cutoff_date,
                    Commitment.status.in_(["pending", "in_progress"])
                )
            ).order_by(Commitment.deadline.asc())
        )
        return list(result.scalars().all())
    
    async def get_active_risks(
        self,
        user_id: str,
        severity: Optional[str] = None
    ) -> List[Risk]:
        """Get active risks, optionally filtered by severity"""
        query = select(Risk).where(
            and_(
                Risk.user_id == user_id,
                Risk.status == "open"
            )
        )
        
        if severity:
            query = query.where(Risk.severity == severity)
        
        query = query.order_by(Risk.urgency_score.desc(), Risk.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_active_opportunities(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Opportunity]:
        """Get active opportunities, optionally filtered by status"""
        query = select(Opportunity).where(
            and_(
                Opportunity.user_id == user_id,
                Opportunity.status.in_(["new", "qualified", "in_progress"])
            )
        )
        
        if status:
            query = query.where(Opportunity.status == status)
        
        query = query.order_by(Opportunity.estimated_value.desc().nullslast(), Opportunity.probability.desc().nullslast())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
