"""
Cold Email Campaign Models

Features:
- Campaign builder
- Lead upload
- Personalization engine
- Multi-step sequences
- A/B testing
- Smart throttling
- Warm-up system
- Bounce handling
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Index

from app.models.database import Base


class Campaign(Base):
    """Email campaign definition"""
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Campaign Identity
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(String, nullable=False, index=True)  # cold_outreach, follow_up, nurture, announcement
    
    # Status
    status = Column(String, default="draft", index=True)  # draft, scheduled, running, paused, completed, cancelled
    
    # Sender Configuration
    from_email = Column(String, nullable=False)
    from_name = Column(String, nullable=True)
    reply_to = Column(String, nullable=True)
    
    # Scheduling
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Delivery Settings
    daily_send_limit = Column(Integer, default=50)  # Max emails per day
    send_delay_minutes = Column(Integer, default=5)  # Delay between sends
    timezone = Column(String, default="UTC")
    send_hours = Column(JSON, default=list)  # Hours of day to send (0-23)
    
    # Warm-up Settings
    warm_up_enabled = Column(Boolean, default=False)
    warm_up_emails_per_day = Column(Integer, default=5)
    
    # A/B Testing
    ab_test_enabled = Column(Boolean, default=False)
    ab_test_split = Column(Float, default=0.5)  # 50/50 split
    
    # Statistics
    total_leads = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_delivered = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    replies_received = Column(Integer, default=0)
    bounces = Column(Integer, default=0)
    unsubscribes = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_campaigns_user_status', 'user_id', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "campaign_type": self.campaign_type,
            "status": self.status,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "reply_to": self.reply_to,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "daily_send_limit": self.daily_send_limit,
            "send_delay_minutes": self.send_delay_minutes,
            "timezone": self.timezone,
            "send_hours": self.send_hours or [],
            "warm_up_enabled": self.warm_up_enabled,
            "warm_up_emails_per_day": self.warm_up_emails_per_day,
            "ab_test_enabled": self.ab_test_enabled,
            "ab_test_split": self.ab_test_split,
            "total_leads": self.total_leads,
            "emails_sent": self.emails_sent,
            "emails_delivered": self.emails_delivered,
            "emails_opened": self.emails_opened,
            "emails_clicked": self.emails_clicked,
            "replies_received": self.replies_received,
            "bounces": self.bounces,
            "unsubscribes": self.unsubscribes,
            "tags": self.tags or [],
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class CampaignSequence(Base):
    """Multi-step email sequence for a campaign"""
    __tablename__ = "campaign_sequences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Sequence Step
    step_order = Column(Integer, nullable=False)  # Order in sequence
    name = Column(String, nullable=False)
    
    # Email Content
    subject_template = Column(String, nullable=False)  # Can include {name}, {company}, etc.
    body_template = Column(Text, nullable=False)  # Can include personalization variables
    
    # Timing
    delay_days = Column(Integer, default=0)  # Days to wait before sending this step
    delay_hours = Column(Integer, default=0)  # Additional hours
    
    # Conditions
    send_if_opened = Column(Boolean, default=False)  # Only send if previous email was opened
    send_if_clicked = Column(Boolean, default=False)  # Only send if previous email was clicked
    send_if_replied = Column(Boolean, default=False)  # Only send if previous email was replied to
    stop_if_replied = Column(Boolean, default=True)  # Stop sequence if recipient replies
    
    # A/B Testing Variants
    variant_a_subject = Column(String, nullable=True)
    variant_a_body = Column(Text, nullable=True)
    variant_b_subject = Column(String, nullable=True)
    variant_b_body = Column(Text, nullable=True)
    
    # Metadata
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_campaign_order', 'campaign_id', 'step_order'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "step_order": self.step_order,
            "name": self.name,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "delay_days": self.delay_days,
            "delay_hours": self.delay_hours,
            "send_if_opened": self.send_if_opened,
            "send_if_clicked": self.send_if_clicked,
            "send_if_replied": self.send_if_replied,
            "stop_if_replied": self.stop_if_replied,
            "variant_a_subject": self.variant_a_subject,
            "variant_a_body": self.variant_a_body,
            "variant_b_subject": self.variant_b_subject,
            "variant_b_body": self.variant_b_body,
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Lead(Base):
    """Lead/recipient for campaigns"""
    __tablename__ = "leads"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Lead Identity
    email = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    
    # Personalization Data
    custom_fields = Column(JSON, default=dict)  # Additional fields for personalization
    
    # Status
    status = Column(String, default="pending", index=True)  # pending, sent, delivered, opened, clicked, replied, bounced, unsubscribed, completed
    
    # Sequence Tracking
    current_sequence_step = Column(Integer, default=0)
    last_email_sent_at = Column(DateTime, nullable=True)
    next_email_scheduled_at = Column(DateTime, nullable=True, index=True)
    
    # Engagement
    first_opened_at = Column(DateTime, nullable=True)
    last_opened_at = Column(DateTime, nullable=True)
    first_clicked_at = Column(DateTime, nullable=True)
    last_clicked_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    
    # A/B Testing
    ab_test_variant = Column(String, nullable=True)  # A or B
    
    # Metadata
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy conflict
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_campaign_status', 'campaign_id', 'status'),
        Index('idx_scheduled', 'next_email_scheduled_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "user_id": self.user_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company": self.company,
            "job_title": self.job_title,
            "custom_fields": self.custom_fields or {},
            "status": self.status,
            "current_sequence_step": self.current_sequence_step,
            "last_email_sent_at": self.last_email_sent_at.isoformat() if self.last_email_sent_at else None,
            "next_email_scheduled_at": self.next_email_scheduled_at.isoformat() if self.next_email_scheduled_at else None,
            "first_opened_at": self.first_opened_at.isoformat() if self.first_opened_at else None,
            "last_opened_at": self.last_opened_at.isoformat() if self.last_opened_at else None,
            "first_clicked_at": self.first_clicked_at.isoformat() if self.first_clicked_at else None,
            "last_clicked_at": self.last_clicked_at.isoformat() if self.last_clicked_at else None,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
            "ab_test_variant": self.ab_test_variant,
            "tags": self.tags or [],
            "metadata": self.extra_data or {},  # Keep API field name as 'metadata' for backward compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class WarmupSchedule(Base):
    """Warm-up schedule for campaign sending"""
    __tablename__ = "warmup_schedules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    day_of_week = Column(String, nullable=False, index=True)  # Monday, Tuesday, ...
    send_limit = Column(Integer, default=5)
    is_active = Column(Boolean, default=True, index=True)

    last_executed = Column(DateTime, nullable=True)
    emails_sent_today = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_warmup_campaign_day', 'campaign_id', 'day_of_week'),
    )
