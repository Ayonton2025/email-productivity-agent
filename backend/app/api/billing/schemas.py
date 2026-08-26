"""Validated request and response contracts shared by billing routers."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class SubscriptionResponse(BaseModel):
    id: str
    plan_id: str
    plan_name: str
    status: str
    current_period_end: datetime
    ai_credits_monthly: int
    ai_credits_used: int
    outbound_credits_monthly: int
    outbound_credits_used: int
    team_members_limit: int
    team_members_current: int

    class Config:
        from_attributes = True


class UpgradeRequest(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=50)
    payment_method: Literal["auto", "paystack", "paypal", "stripe", "crypto"] = "auto"
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    prefer_local_currency: bool = False

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class PaymentMethodUpdateRequest(BaseModel):
    payment_method: Literal["paystack", "paypal", "stripe", "crypto"]


class CouponRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class CreditsResponse(BaseModel):
    ai_credits: dict
    balance_usd: float = Field(..., ge=0)


class CreditTopupRequest(BaseModel):
    credits: int = Field(..., gt=0, le=1_000_000)
    email: EmailStr
    country_code: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class AvailablePlansResponse(BaseModel):
    plans: dict
