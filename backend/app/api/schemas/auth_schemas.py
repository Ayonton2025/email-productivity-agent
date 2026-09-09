from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.input_validation import ValidatedRequestModel


def validate_password_complexity(value: str) -> str:
    if not any(character.isupper() for character in value):
        raise ValueError("Password must contain uppercase letter")
    if not any(character.islower() for character in value):
        raise ValueError("Password must contain lowercase letter")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password must contain digit")
    if not any(character in "!@#$%^&*()_+-=[]{}|;:,.<>?" for character in value):
        raise ValueError("Password must contain special character")
    return value


class LoginRequest(ValidatedRequestModel):
    """Login request schema"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, max_length=72, description="User password")


class RegisterRequest(ValidatedRequestModel):
    """User registration request schema"""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    password: str = Field(
        ...,
        min_length=12,
        max_length=72,
        description="Password (12-72 chars, including uppercase, lowercase, number, and special character)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_complexity(value)


class ForgotPasswordRequest(ValidatedRequestModel):
    email: EmailStr


class ResetPasswordRequest(ValidatedRequestModel):
    token: str = Field(..., min_length=16, max_length=4096)
    new_password: str = Field(..., min_length=12, max_length=72)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_complexity(value)


class TokenResponse(BaseModel):
    """Token response schema"""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
