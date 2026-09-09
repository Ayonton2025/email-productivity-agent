from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.input_validation import ValidatedRequestModel


class AgentProcessRequest(ValidatedRequestModel):
    email_id: str = Field(..., min_length=1, max_length=255)
    prompt_type: str = Field(..., min_length=1, max_length=100)
    custom_prompt: Optional[str] = Field(default=None, min_length=1, max_length=100000)
    system_prompt: Optional[str] = Field(default=None, min_length=1, max_length=255)


class AgentChatRequest(ValidatedRequestModel):
    message: str = Field(..., min_length=1, max_length=100000)
