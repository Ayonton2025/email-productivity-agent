from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.input_validation import ValidatedRequestModel

from .common import EmailCategory


class EmailBase(ValidatedRequestModel):
    """Base email schema"""

    subject: str = Field(..., min_length=1, max_length=1000, description="Email subject")
    body_text: Optional[str] = Field(None, max_length=100000, description="Plain text body")
    body_html: Optional[str] = Field(None, max_length=100000, description="HTML body")


class EmailRequest(EmailBase):
    """Request schema for creating/updating emails"""

    recipient: EmailStr = Field(..., description="Recipient email address")


class EmailResponse(EmailBase):
    """Response schema for email data"""

    id: int
    sender: str
    recipients: List[str]
    received_at: datetime
    is_read: bool
    is_flagged: bool
    ai_category: Optional[EmailCategory] = None
    ai_summary: Optional[str] = None

    class Config:
        from_attributes = True


class DraftCreateRequest(ValidatedRequestModel):
    subject: str = Field(..., min_length=1, max_length=1000)
    body: str = Field(default="", max_length=100000)
    recipient: Optional[EmailStr] = None
    context_email_id: Optional[str] = Field(default=None, max_length=255)
    metadata: dict = Field(default_factory=dict)

    @field_validator("recipient", mode="before")
    @classmethod
    def blank_recipient_is_none(cls, value: object) -> object:
        return None if value == "" else value


class DraftUpdateRequest(ValidatedRequestModel):
    subject: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    body: Optional[str] = Field(default=None, max_length=100000)
    recipient: Optional[EmailStr] = None
    context_email_id: Optional[str] = Field(default=None, max_length=255)
    metadata: Optional[dict] = None

    @field_validator("recipient", mode="before")
    @classmethod
    def blank_recipient_is_none(cls, value: object) -> object:
        return None if value == "" else value


class EmailAccountRequest(ValidatedRequestModel):
    """Email account connection request"""

    provider: Literal["gmail", "outlook", "yahoo"]
    access_token: str = Field(..., min_length=1, max_length=8192)
    refresh_token: Optional[str] = Field(None, max_length=8192)


class GmailConnectionRequest(ValidatedRequestModel):
    """Request schema for connecting a Gmail account with OAuth tokens."""

    email: EmailStr
    access_token: str = Field(..., min_length=1, max_length=8192)
    refresh_token: Optional[str] = Field(default=None, max_length=8192)
    token_expiry: Optional[datetime] = None


class EmailAccountResponse(BaseModel):
    """Email account response schema"""

    id: str
    email: EmailStr
    provider: str
    status: str
    last_sync: Optional[datetime] = None
    total_emails: int


class BulkEmailActionRequest(ValidatedRequestModel):
    """Request for bulk email operations"""

    email_ids: List[int] = Field(..., min_length=1, max_length=1000, description="Email IDs to operate on")

    @field_validator("email_ids")
    @classmethod
    def validate_ids(cls, v: List[int]) -> List[int]:
        """Ensure unique IDs"""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate email IDs provided")
        return v


class BulkMarkReadRequest(BulkEmailActionRequest):
    """Request to mark multiple emails as read/unread"""

    is_read: bool = Field(..., description="Mark as read (true) or unread (false)")


class BulkFlagRequest(BulkEmailActionRequest):
    """Request to flag/unflag multiple emails"""

    is_flagged: bool = Field(..., description="Flag (true) or unflag (false)")


class BulkCategorizeRequest(BulkEmailActionRequest):
    """Request to categorize multiple emails"""

    category: EmailCategory = Field(..., description="Category to assign")


class BulkDeleteRequest(BulkEmailActionRequest):
    """Request to delete multiple emails"""

    soft_delete: bool = Field(default=True, description="Soft delete or permanent delete")


class SearchRequest(ValidatedRequestModel):
    """Search request schema"""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(default=50, ge=1, le=500, description="Results per page")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    category: Optional[EmailCategory] = Field(None, description="Filter by category")
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    is_flagged: Optional[bool] = Field(None, description="Filter by flag status")


class AdvancedSearchRequest(ValidatedRequestModel):
    """Advanced search request with multiple filters"""

    keywords: str = Field(..., min_length=1, max_length=1000, description="Search keywords")
    search_fields: Literal["all", "subject", "sender", "body"] = "all"
    from_address: Optional[EmailStr] = Field(None, description="Filter by sender")
    category: Optional[EmailCategory] = Field(None, description="Filter by category")
    date_from: Optional[datetime] = Field(None, description="Start date")
    date_to: Optional[datetime] = Field(None, description="End date")
    has_attachments: Optional[bool] = Field(None, description="Has attachments")
    is_unread_only: bool = Field(default=False, description="Only unread emails")
    limit: int = Field(default=50, ge=1, le=500, description="Results per page")


class SyncHistoryResponse(BaseModel):
    """Sync operation history response"""

    id: str
    sync_type: str = Field(..., description="incremental or full")
    status: str = Field(..., description="completed, failed, or partial")
    emails_processed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None


class SyncStatsResponse(BaseModel):
    """Sync statistics response"""

    total_syncs: int
    completed_syncs: int
    failed_syncs: int
    success_rate: float
    total_emails_synced: int
    avg_emails_per_sync: float
    last_sync_time: Optional[datetime] = None
    last_sync_status: Optional[str] = None
