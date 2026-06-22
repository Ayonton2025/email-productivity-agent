"""
Email security and scam detection models.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, Float, ForeignKey, Index

from app.models.database import Base


class EmailSecurityScan(Base):
    __tablename__ = "email_security_scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)

    scam_score = Column(Float, default=0.0, index=True)
    phishing_signals = Column(JSON, default=list)
    verdict = Column(String, default="safe", index=True)  # safe, suspicious, dangerous
    rationale = Column(Text, nullable=True)
    model = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_security_user_verdict", "user_id", "verdict"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_id": self.email_id,
            "scam_score": self.scam_score,
            "phishing_signals": self.phishing_signals or [],
            "verdict": self.verdict,
            "rationale": self.rationale,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
        }
