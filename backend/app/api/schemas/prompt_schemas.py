from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.input_validation import ValidatedRequestModel


class PromptCreateRequest(ValidatedRequestModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    template: str = Field(..., min_length=1, max_length=100000)
    category: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    metadata: dict = Field(default_factory=dict)


class PromptUpdateRequest(ValidatedRequestModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    template: Optional[str] = Field(default=None, min_length=1, max_length=100000)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None
