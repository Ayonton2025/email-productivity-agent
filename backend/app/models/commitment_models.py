"""
Decision Intelligence Models:
- Commitments (deadlines, promises, agreements)
- Risks (legal, compliance, payment delays, angry emails)
- Opportunities (sales leads, partnerships, jobs, funding)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Index

from app.models.database import Base


class Commitment(Base):
    """Extracted commitments, deadlines, and promises from emails"""
    __tablename__ = "commitments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("contacts.id"), nullable=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True, index=True)
    
    # Commitment Details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    commitment_type = Column(String, nullable=False, index=True)  # deadline, promise, agreement, task, meeting
    
    # Who committed
    committed_by = Column(String, nullable=True)  # "user" or "contact" or email address
    is_user_commitment = Column(Boolean, default=False)  # True if user committed, False if contact committed
    
    # Deadline & Status
    deadline = Column(DateTime, nullable=True, index=True)
    is_overdue = Column(Boolean, default=False, index=True)
    status = Column(String, default="pending", index=True)  # pending, in_progress, completed, cancelled, missed
    
    # Priority & Impact
    priority = Column(String, default="medium")  # high, medium, low
    revenue_impact = Column(Float, nullable=True)  # Estimated revenue impact
    business_impact = Column(String, nullable=True)  # critical, high, medium, low
    
    # Metadata
    extracted_text = Column(Text, nullable=True)  # Original text that was extracted
    confidence_score = Column(Float, default=0.0)  # AI confidence in extraction
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_commitments_user_status', 'user_id', 'status'),
        Index('idx_commitments_deadline', 'deadline'),
        Index('idx_commitments_overdue', 'is_overdue', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_id": self.email_id,
            "contact_id": self.contact_id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "commitment_type": self.commitment_type,
            "committed_by": self.committed_by,
            "is_user_commitment": self.is_user_commitment,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "is_overdue": self.is_overdue,
            "status": self.status,
            "priority": self.priority,
            "revenue_impact": self.revenue_impact,
            "business_impact": self.business_impact,
            "extracted_text": self.extracted_text,
            "confidence_score": self.confidence_score,
            "tags": self.tags or [],
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Risk(Base):
    """Identified risks from emails (legal, compliance, payment delays, angry emails)"""
    __tablename__ = "risks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("contacts.id"), nullable=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True, index=True)
    
    # Risk Details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    risk_type = Column(String, nullable=False, index=True)  # legal, compliance, payment_delay, angry, churn, data_breach, etc.
    severity = Column(String, nullable=False, index=True)  # critical, high, medium, low
    
    # Risk Status
    status = Column(String, default="open", index=True)  # open, investigating, mitigated, resolved, false_positive
    is_acknowledged = Column(Boolean, default=False)
    
    # Impact Assessment
    potential_impact = Column(Text, nullable=True)
    revenue_impact = Column(Float, nullable=True)  # Estimated negative revenue impact
    urgency_score = Column(Float, default=0.0)  # 0-100
    
    # Metadata
    extracted_text = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_risks_user_severity', 'user_id', 'severity'),
        Index('idx_risks_user_status', 'user_id', 'status'),
        Index('idx_risks_type', 'risk_type', 'severity'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_id": self.email_id,
            "contact_id": self.contact_id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "risk_type": self.risk_type,
            "severity": self.severity,
            "status": self.status,
            "is_acknowledged": self.is_acknowledged,
            "potential_impact": self.potential_impact,
            "revenue_impact": self.revenue_impact,
            "urgency_score": self.urgency_score,
            "extracted_text": self.extracted_text,
            "confidence_score": self.confidence_score,
            "tags": self.tags or [],
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class Opportunity(Base):
    """Identified opportunities (sales leads, partnerships, jobs, funding)"""
    __tablename__ = "opportunities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("contacts.id"), nullable=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True, index=True)
    
    # Opportunity Details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    opportunity_type = Column(String, nullable=False, index=True)  # sales_lead, partnership, job, funding, collaboration, etc.
    
    # Status & Stage
    status = Column(String, default="new", index=True)  # new, qualified, in_progress, won, lost, closed
    stage = Column(String, nullable=True)  # discovery, proposal, negotiation, closed
    
    # Value Assessment
    estimated_value = Column(Float, nullable=True)  # Estimated revenue/value
    probability = Column(Float, nullable=True)  # 0-100, probability of closing
    priority = Column(String, default="medium")  # high, medium, low
    
    # Lead Temperature
    lead_temperature = Column(String, nullable=True, index=True)  # hot, warm, cold
    interest_level = Column(String, nullable=True)  # high, medium, low
    
    # Timeline
    expected_close_date = Column(DateTime, nullable=True, index=True)
    
    # Metadata
    extracted_text = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_opportunities_user_status', 'user_id', 'status'),
        Index('idx_opportunities_type', 'opportunity_type', 'status'),
        Index('idx_opportunities_lead_temp', 'lead_temperature', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_id": self.email_id,
            "contact_id": self.contact_id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "opportunity_type": self.opportunity_type,
            "status": self.status,
            "stage": self.stage,
            "estimated_value": self.estimated_value,
            "probability": self.probability,
            "priority": self.priority,
            "lead_temperature": self.lead_temperature,
            "interest_level": self.interest_level,
            "expected_close_date": self.expected_close_date.isoformat() if self.expected_close_date else None,
            "extracted_text": self.extracted_text,
            "confidence_score": self.confidence_score,
            "tags": self.tags or [],
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
