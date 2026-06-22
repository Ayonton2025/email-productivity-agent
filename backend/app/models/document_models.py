"""
Document and Attachment Management Models
Stores metadata about files attached to emails and AI analysis results
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from datetime import datetime
import uuid

from app.models.database import Base


class EmailAttachment(Base):
    __tablename__ = "email_attachments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email_id = Column(String, ForeignKey('emails.id'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    
    # File Metadata
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)  # application/pdf, image/png, etc
    file_size = Column(Integer, nullable=False)  # Bytes
    file_hash = Column(String, nullable=True, unique=True)  # SHA256 for deduplication
    
    # Storage Info
    storage_path = Column(String, nullable=False)  # Path where file is stored (S3, local disk, etc)
    storage_type = Column(String, default="local")  # local, s3, azure_blob, etc
    is_downloadable = Column(Boolean, default=True)
    
    # Metadata
    extension = Column(String, nullable=True)  # pdf, docx, txt, etc
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "email_id": self.email_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "extension": self.extension,
            "is_downloadable": self.is_downloadable,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentAnalysis(Base):
    """Store AI analysis results of documents"""
    __tablename__ = "document_analysis"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    attachment_id = Column(String, ForeignKey('email_attachments.id'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    
    # Analysis Results
    analysis_type = Column(String, nullable=False)  # "summary", "extraction", "classification", etc
    
    # Free tier: metadata only
    file_name = Column(String, nullable=False)
    file_extension = Column(String, nullable=True)
    file_size_display = Column(String, nullable=True)  # "2.5 MB"
    extracted_title = Column(String, nullable=True)  # Title extracted from first page (if available)
    page_count = Column(Integer, nullable=True)  # For PDF, DOCX
    
    # Paid tier: full analysis
    summary = Column(Text, nullable=True)  # Short AI summary
    key_points = Column(JSON, default=list)  # Key points extracted
    entities = Column(JSON, default=list)  # Named entities (people, companies, dates)
    sentiment = Column(String, nullable=True)  # Positive, Negative, Neutral
    language = Column(String, nullable=True)  # Detected language
    is_full_analysis = Column(Boolean, default=False)  # True if user is paid and got full analysis
    
    # Admin control
    is_sensitive = Column(Boolean, default=False)  # Flag for sensitive content
    confidence_score = Column(Integer, nullable=True)  # 0-100 confidence in analysis
    
    # Metadata
    analysis_status = Column(String, default="pending")  # pending, processing, completed, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, include_full_analysis=False):
        base = {
            "id": self.id,
            "attachment_id": self.attachment_id,
            "file_name": self.file_name,
            "file_extension": self.file_extension,
            "file_size_display": self.file_size_display,
            "extracted_title": self.extracted_title,
            "page_count": self.page_count,
            "analysis_status": self.analysis_status,
        }
        
        if include_full_analysis or self.is_full_analysis:
            base.update({
                "summary": self.summary,
                "key_points": self.key_points,
                "entities": self.entities,
                "sentiment": self.sentiment,
                "language": self.language,
                "confidence_score": self.confidence_score,
            })
        else:
            # Free tier: show upgrade message
            base["upgrade_message"] = "📄 To read full document analysis, please upgrade your subscription"
        
        return base
