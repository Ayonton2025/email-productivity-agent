"""
API Request/Response Validation Schemas

Defines Pydantic models for strict input validation across all API endpoints.
Ensures data integrity and provides automatic OpenAPI documentation.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EmailCategory(str, Enum):
    """Valid email categories"""
    WORK = "work"
    PERSONAL = "personal"
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    SOCIAL = "social"
    OTHER = "other"


# ============================================================================
# EMAIL ENDPOINTS
# ============================================================================

class EmailBase(BaseModel):
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


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RegisterRequest(BaseModel):
    """User registration request schema"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    password: str = Field(
        ...,
        min_length=8,
        description="Password (min 8 chars, must include uppercase, number, special char)"
    )

    @validator("password")
    def validate_password(cls, v):
        """Ensure password has complexity"""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain special character")
        return v


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


# ============================================================================
# EMAIL ACCOUNT ENDPOINTS
# ============================================================================

class EmailAccountRequest(BaseModel):
    """Email account connection request"""
    provider: str = Field(..., description="Email provider (gmail, outlook, yahoo)")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")


class EmailAccountResponse(BaseModel):
    """Email account response schema"""
    id: str
    email: EmailStr
    provider: str
    status: str
    last_sync: Optional[datetime] = None
    total_emails: int


# ============================================================================
# BULK OPERATIONS ENDPOINTS
# ============================================================================

class BulkEmailActionRequest(BaseModel):
    """Request for bulk email operations"""
    email_ids: List[int] = Field(..., min_items=1, max_items=1000, description="Email IDs to operate on")

    @validator("email_ids")
    def validate_ids(cls, v):
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


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

class SearchRequest(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(default=50, ge=1, le=500, description="Results per page")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    category: Optional[EmailCategory] = Field(None, description="Filter by category")
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    is_flagged: Optional[bool] = Field(None, description="Filter by flag status")


class AdvancedSearchRequest(BaseModel):
    """Advanced search request with multiple filters"""
    keywords: str = Field(..., min_length=1, description="Search keywords")
    search_fields: str = Field(default="all", description="Fields to search")
    from_address: Optional[str] = Field(None, description="Filter by sender")
    category: Optional[EmailCategory] = Field(None, description="Filter by category")
    date_from: Optional[datetime] = Field(None, description="Start date")
    date_to: Optional[datetime] = Field(None, description="End date")
    has_attachments: Optional[bool] = Field(None, description="Has attachments")
    is_unread_only: bool = Field(default=False, description="Only unread emails")
    limit: int = Field(default=50, ge=1, le=500, description="Results per page")


# ============================================================================
# SYNC HISTORY ENDPOINTS
# ============================================================================

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


# ============================================================================
# SHARED RESPONSE SCHEMAS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    service: str = Field(default="bylix-email-platform")
    version: str
    timestamp: datetime
    dependencies: dict = Field(default_factory=dict, description="Status of dependencies")


class ErrorResponse(BaseModel):
    """Standard error response"""
    status: str = Field(default="error")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper"""
    data: List[dict]
    total: int
    offset: int
    limit: int
    has_more: bool
