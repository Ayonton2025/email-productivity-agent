from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.input_validation import ValidatedRequestModel


class EmailCategory(str, Enum):
    """Valid email categories"""

    WORK = "work"
    PERSONAL = "personal"
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    SOCIAL = "social"
    OTHER = "other"


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
