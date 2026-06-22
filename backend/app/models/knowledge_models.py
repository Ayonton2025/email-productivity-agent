"""
Knowledge base models (email-to-knowledge with embeddings).
"""

from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Index

from app.models.database import Base


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, default=list)  # JSON fallback; can be moved to pgvector in production.
    source = Column(String, default="email")
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_knowledge_user_source", "user_id", "source"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_id": self.email_id,
            "title": self.title,
            "content": self.content,
            "embedding": self.embedding or [],
            "source": self.source,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
