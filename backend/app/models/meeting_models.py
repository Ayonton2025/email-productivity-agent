"""
Meeting intelligence models.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, ForeignKey, Index

from app.models.database import Base


class MeetingRecord(Base):
    __tablename__ = "meeting_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)

    title = Column(String, nullable=False)
    attendees = Column(JSON, default=list)
    proposed_slots = Column(JSON, default=list)
    selected_slot = Column(String, nullable=True)
    agenda = Column(Text, nullable=True)
    prep_notes = Column(Text, nullable=True)
    post_summary = Column(Text, nullable=True)
    status = Column(String, default="proposed", index=True)  # proposed, scheduled, completed
    confidence = Column(Integer, default=70)
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_meeting_user_status", "user_id", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_id": self.email_id,
            "title": self.title,
            "attendees": self.attendees or [],
            "proposed_slots": self.proposed_slots or [],
            "selected_slot": self.selected_slot,
            "agenda": self.agenda,
            "prep_notes": self.prep_notes,
            "post_summary": self.post_summary,
            "status": self.status,
            "confidence": self.confidence,
            "metadata": self.extra_data or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
