"""
Contact and relationship intelligence models.

Auto-builds contact profiles from emails:
- Communication frequency tracking
- Relationship status (cold/warming/active/ghosting)
- Conversation sentiment over time
- Decision-maker detection
- Company aggregation
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Index
from sqlalchemy.orm import relationship

from app.models.database import Base


class Contact(Base):
    """Contact profile auto-built from email interactions"""
    __tablename__ = "contacts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True, index=True)
    
    # Contact Identity
    email = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Role & Title (extracted from email signatures, LinkedIn, etc.)
    job_title = Column(String, nullable=True)
    department = Column(String, nullable=True)
    role_type = Column(String, nullable=True)  # decision_maker, influencer, user, admin, etc.
    is_decision_maker = Column(Boolean, default=False, index=True)
    
    # Relationship Intelligence
    relationship_status = Column(String, default="cold", index=True)  # cold, warming, active, ghosting, dormant
    relationship_score = Column(Float, default=0.0)  # 0-100, based on frequency, recency, sentiment
    trust_score = Column(Float, default=50.0)
    stress_level = Column(Float, default=50.0)
    loyalty_score = Column(Float, default=50.0)
    needs_crm_sync = Column(Boolean, default=False, index=True)
    last_synced_at = Column(DateTime, nullable=True)
    
    # Communication Metrics
    total_emails_sent = Column(Integer, default=0)
    total_emails_received = Column(Integer, default=0)
    last_contact_date = Column(DateTime, nullable=True, index=True)
    first_contact_date = Column(DateTime, nullable=True)
    average_response_time_hours = Column(Float, nullable=True)  # Average time to respond to their emails
    
    # Sentiment Tracking
    overall_sentiment = Column(String, nullable=True)  # positive, neutral, negative
    sentiment_trend = Column(String, nullable=True)  # improving, stable, declining
    last_sentiment_score = Column(Float, nullable=True)  # -1 to 1
    
    # Metadata
    tags = Column(JSON, default=list)  # Custom tags
    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)  # Additional extracted data (renamed from metadata to avoid SQLAlchemy conflict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_email', 'user_id', 'email', unique=True),
        Index('idx_relationship_status', 'user_id', 'relationship_status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "email": self.email,
            "display_name": self.display_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "job_title": self.job_title,
            "department": self.department,
            "role_type": self.role_type,
            "is_decision_maker": self.is_decision_maker,
            "relationship_status": self.relationship_status,
            "relationship_score": self.relationship_score,
            "trust_score": self.trust_score,
            "stress_level": self.stress_level,
            "loyalty_score": self.loyalty_score,
            "total_emails_sent": self.total_emails_sent,
            "total_emails_received": self.total_emails_received,
            "last_contact_date": self.last_contact_date.isoformat() if self.last_contact_date else None,
            "first_contact_date": self.first_contact_date.isoformat() if self.first_contact_date else None,
            "average_response_time_hours": self.average_response_time_hours,
            "overall_sentiment": self.overall_sentiment,
            "sentiment_trend": self.sentiment_trend,
            "last_sentiment_score": self.last_sentiment_score,
            "tags": self.tags or [],
            "notes": self.notes,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "needs_crm_sync": self.needs_crm_sync,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Company(Base):
    """Company aggregation - groups all contacts by company"""
    __tablename__ = "companies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Company Identity
    name = Column(String, nullable=False, index=True)
    domain = Column(String, nullable=True, index=True)  # Extracted from email domains
    website = Column(String, nullable=True)
    
    # Company Intelligence
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)  # startup, small, medium, large, enterprise
    relationship_status = Column(String, default="cold", index=True)  # cold, warming, active, partner, client
    
    # Communication Metrics
    total_contacts = Column(Integer, default=0)
    total_emails = Column(Integer, default=0)
    last_contact_date = Column(DateTime, nullable=True, index=True)
    first_contact_date = Column(DateTime, nullable=True)
    
    # Business Intelligence
    is_client = Column(Boolean, default=False, index=True)
    is_prospect = Column(Boolean, default=False, index=True)
    is_vendor = Column(Boolean, default=False, index=True)
    revenue_impact = Column(Float, nullable=True)  # Estimated revenue impact
    
    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_name', 'user_id', 'name'),
        Index('idx_user_domain', 'user_id', 'domain'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "domain": self.domain,
            "website": self.website,
            "industry": self.industry,
            "company_size": self.company_size,
            "relationship_status": self.relationship_status,
            "total_contacts": self.total_contacts,
            "total_emails": self.total_emails,
            "last_contact_date": self.last_contact_date.isoformat() if self.last_contact_date else None,
            "first_contact_date": self.first_contact_date.isoformat() if self.first_contact_date else None,
            "is_client": self.is_client,
            "is_prospect": self.is_prospect,
            "is_vendor": self.is_vendor,
            "revenue_impact": self.revenue_impact,
            "tags": self.tags or [],
            "notes": self.notes,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ContactInteraction(Base):
    """Tracks individual email interactions for sentiment and pattern analysis"""
    __tablename__ = "contact_interactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    contact_id = Column(String, ForeignKey("contacts.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    
    # Interaction Details
    interaction_type = Column(String, nullable=False)  # sent, received, replied, forwarded
    direction = Column(String, nullable=False)  # inbound, outbound
    subject = Column(String, nullable=True)
    
    # Sentiment Analysis
    sentiment = Column(String, nullable=True)  # positive, neutral, negative
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    
    # Timing
    interaction_date = Column(DateTime, nullable=False, index=True)
    response_time_hours = Column(Float, nullable=True)  # Time to respond (if applicable)
    
    # Metadata
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_contact_date', 'contact_id', 'interaction_date'),
        Index('idx_contact_user_date', 'user_id', 'interaction_date'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "contact_id": self.contact_id,
            "email_id": self.email_id,
            "interaction_type": self.interaction_type,
            "direction": self.direction,
            "subject": self.subject,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "interaction_date": self.interaction_date.isoformat(),
            "response_time_hours": self.response_time_hours,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
        }
