"""
Timeline models for relationship memory view.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Index

from app.models.database import Base


class RelationshipTimelineEvent(Base):
    __tablename__ = "relationship_timeline_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    contact_id = Column(String, ForeignKey("contacts.id"), nullable=True, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    meeting_id = Column(String, nullable=True, index=True)
    task_id = Column(String, nullable=True, index=True)

    event_type = Column(String, nullable=False, index=True)  # email, meeting, task, attachment
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_timeline_user_contact_time", "user_id", "contact_id", "occurred_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "contact_id": self.contact_id,
            "email_id": self.email_id,
            "meeting_id": self.meeting_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "title": self.title,
            "summary": self.summary,
            "metadata": self.extra_data or {},
            "occurred_at": self.occurred_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }
