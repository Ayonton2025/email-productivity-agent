"""
Relationship Intelligence Service

Auto-builds contact profiles from emails:
- Extracts person role, company, sentiment
- Tracks communication frequency
- Updates relationship status (cold/warming/active/ghosting)
- Detects decision-makers
- Aggregates by company
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload

from app.models.database import Email
from app.models.contact_models import Contact, Company, ContactInteraction
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService


def extract_email_domain(email: str) -> Optional[str]:
    """Extract domain from email address"""
    if not email or "@" not in email:
        return None
    return email.split("@")[1].lower().strip()


def extract_name_from_email(email: str, display_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Extract first and last name from email or display name"""
    if display_name:
        parts = display_name.strip().split()
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:])
        elif len(parts) == 1:
            return parts[0], None
    
    # Try to extract from email
    local_part = email.split("@")[0] if "@" in email else email
    parts = re.split(r"[._-]", local_part)
    if len(parts) >= 2:
        return parts[0].capitalize(), parts[-1].capitalize()
    elif len(parts) == 1:
        return parts[0].capitalize(), None
    
    return None, None


class RelationshipService:
    """Service for managing contacts, companies, and relationship intelligence"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)
    
    async def process_email_for_relationships(self, email: Email) -> Dict[str, Any]:
        """
        Process an email to extract relationship intelligence and update/create contacts/companies.
        Returns dict with contact_id, company_id, and extracted metadata.
        """
        if not email.sender:
            return {"contact_id": None, "company_id": None}
        
        # Extract email and domain
        sender_email = email.sender.lower().strip()
        domain = extract_email_domain(sender_email)
        
        # Get or create contact
        contact = await self.get_or_create_contact(
            user_id=email.user_id,
            email=sender_email,
            display_name=email.sender
        )
        
        # Get or create company
        company = None
        if domain:
            company = await self.get_or_create_company(
                user_id=email.user_id,
                domain=domain,
                name=domain.split(".")[0].capitalize()  # Fallback name
            )
            
            # Link contact to company if not already linked
            if contact.company_id != company.id:
                contact.company_id = company.id
                await self.db.commit()
        
        # Extract additional intelligence using AI
        extracted_data = await self.extract_contact_intelligence(email, contact)
        
        # Update contact with extracted data
        if extracted_data:
            await self.update_contact_from_extraction(contact, extracted_data)
        
        # Record interaction
        await self.record_interaction(
            user_id=email.user_id,
            contact_id=contact.id,
            email_id=email.id,
            direction="inbound",
            interaction_type="received",
            subject=email.subject,
            sentiment=email.sentiment,
            interaction_date=email.received_at
        )
        
        # Update relationship metrics
        await self.update_relationship_metrics(contact)
        
        await self.db.commit()
        
        return {
            "contact_id": contact.id,
            "company_id": company.id if company else None,
            "extracted_data": extracted_data
        }
    
    async def get_or_create_contact(
        self,
        user_id: str,
        email: str,
        display_name: Optional[str] = None
    ) -> Contact:
        """Get existing contact or create new one"""
        result = await self.db.execute(
            select(Contact).where(
                and_(Contact.user_id == user_id, Contact.email == email.lower())
            )
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            first_name, last_name = extract_name_from_email(email, display_name)
            contact = Contact(
                user_id=user_id,
                email=email.lower(),
                display_name=display_name,
                first_name=first_name,
                last_name=last_name,
                relationship_status="cold",
                first_contact_date=datetime.utcnow()
            )
            self.db.add(contact)
            await self.db.flush()
        
        return contact
    
    async def get_or_create_company(
        self,
        user_id: str,
        domain: str,
        name: Optional[str] = None
    ) -> Company:
        """Get existing company or create new one"""
        result = await self.db.execute(
            select(Company).where(
                and_(Company.user_id == user_id, Company.domain == domain.lower())
            )
        )
        company = result.scalar_one_or_none()
        
        if not company:
            company = Company(
                user_id=user_id,
                domain=domain.lower(),
                name=name or domain.split(".")[0].capitalize(),
                relationship_status="cold",
                first_contact_date=datetime.utcnow()
            )
            self.db.add(company)
            await self.db.flush()
        
        return company
    
    async def extract_contact_intelligence(
        self,
        email: Email,
        contact: Contact
    ) -> Optional[Dict[str, Any]]:
        """Use AI to extract person role, company, sentiment, urgency from email"""
        try:
            email_content = (
                f"From: {email.sender}\n"
                f"Subject: {email.subject}\n"
                f"Body: {(email.body_text or email.body_html or '')[:4000]}"
            )
            
            prompt = f"""Extract relationship intelligence from this email. Return JSON with:
{{
  "person_role": "job title or role (e.g., CEO, Manager, Developer)",
  "department": "department name if mentioned",
  "is_decision_maker": true/false,
  "company_name": "company name if mentioned",
  "sentiment": "positive/neutral/negative",
  "urgency": "high/medium/low",
  "relationship_context": "brief context about relationship"
}}

Email:
{email_content}

Return only valid JSON."""

            response = await self.llm_service.process_prompt(prompt, "")
            
            # Parse JSON response
            import json
            try:
                if isinstance(response, str):
                    # Try to extract JSON from response
                    json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                    if json_match:
                        extracted = json.loads(json_match.group())
                    else:
                        extracted = json.loads(response)
                else:
                    extracted = response
                
                return extracted
            except (json.JSONDecodeError, AttributeError):
                return None
        except Exception as e:
            print(f"⚠️ [RelationshipService] Failed to extract intelligence: {e}")
            return None
    
    async def update_contact_from_extraction(
        self,
        contact: Contact,
        extracted_data: Dict[str, Any]
    ):
        """Update contact with extracted intelligence"""
        if extracted_data.get("person_role"):
            contact.job_title = extracted_data["person_role"]
        
        if extracted_data.get("department"):
            contact.department = extracted_data["department"]
        
        if extracted_data.get("is_decision_maker") is True:
            contact.is_decision_maker = True
            contact.role_type = "decision_maker"
        
        if extracted_data.get("sentiment"):
            sentiment = extracted_data["sentiment"].lower()
            contact.last_sentiment_score = 0.5 if sentiment == "positive" else -0.5 if sentiment == "negative" else 0.0
            contact.overall_sentiment = sentiment
    
    async def record_interaction(
        self,
        user_id: str,
        contact_id: str,
        email_id: Optional[str],
        direction: str,
        interaction_type: str,
        subject: Optional[str],
        sentiment: Optional[str],
        interaction_date: datetime
    ):
        """Record an email interaction for tracking"""
        interaction = ContactInteraction(
            user_id=user_id,
            contact_id=contact_id,
            email_id=email_id,
            interaction_type=interaction_type,
            direction=direction,
            subject=subject,
            sentiment=sentiment,
            sentiment_score=0.5 if sentiment == "positive" else -0.5 if sentiment == "negative" else 0.0,
            interaction_date=interaction_date
        )
        self.db.add(interaction)
    
    async def update_relationship_metrics(self, contact: Contact):
        """Update relationship metrics based on interaction history"""
        # Count interactions
        sent_count = await self.db.execute(
            select(func.count(ContactInteraction.id)).where(
                and_(
                    ContactInteraction.contact_id == contact.id,
                    ContactInteraction.direction == "outbound"
                )
            )
        )
        received_count = await self.db.execute(
            select(func.count(ContactInteraction.id)).where(
                and_(
                    ContactInteraction.contact_id == contact.id,
                    ContactInteraction.direction == "inbound"
                )
            )
        )
        
        contact.total_emails_sent = sent_count.scalar() or 0
        contact.total_emails_received = received_count.scalar() or 0
        
        # Get last interaction
        last_interaction = await self.db.execute(
            select(ContactInteraction).where(
                ContactInteraction.contact_id == contact.id
            ).order_by(ContactInteraction.interaction_date.desc()).limit(1)
        )
        last = last_interaction.scalar_one_or_none()
        if last:
            contact.last_contact_date = last.interaction_date
        
        # Calculate relationship status
        days_since_last_contact = (datetime.utcnow() - contact.last_contact_date).days if contact.last_contact_date else 999
        
        total_interactions = contact.total_emails_sent + contact.total_emails_received
        
        if total_interactions == 0:
            contact.relationship_status = "cold"
        elif days_since_last_contact > 90:
            contact.relationship_status = "ghosting" if total_interactions > 3 else "dormant"
        elif days_since_last_contact > 30:
            contact.relationship_status = "dormant"
        elif total_interactions >= 10:
            contact.relationship_status = "active"
        elif total_interactions >= 3:
            contact.relationship_status = "warming"
        else:
            contact.relationship_status = "cold"
        
        # Calculate relationship score (0-100)
        score = 0.0
        score += min(total_interactions * 5, 40)  # Up to 40 points for frequency
        score += max(0, 30 - days_since_last_contact)  # Up to 30 points for recency
        if contact.is_decision_maker:
            score += 10  # 10 points for decision maker
        if contact.overall_sentiment == "positive":
            score += 10  # 10 points for positive sentiment
        elif contact.overall_sentiment == "negative":
            score -= 10  # Penalty for negative
        
        contact.relationship_score = max(0, min(100, score))
    
    async def get_contacts_by_company(self, user_id: str, company_id: str) -> List[Contact]:
        """Get all contacts for a company"""
        result = await self.db.execute(
            select(Contact).where(
                and_(Contact.user_id == user_id, Contact.company_id == company_id)
            ).order_by(Contact.relationship_score.desc())
        )
        return list(result.scalars().all())
    
    async def get_companies(self, user_id: str, status: Optional[str] = None) -> List[Company]:
        """Get all companies for a user, optionally filtered by status"""
        query = select(Company).where(Company.user_id == user_id)
        if status:
            query = query.where(Company.relationship_status == status)
        query = query.order_by(Company.last_contact_date.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
