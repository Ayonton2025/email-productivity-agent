"""Shared validation policy for API request bodies."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ValidatedRequestModel(BaseModel):
    """Secure defaults applied to request DTOs in addition to field constraints."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_unsafe_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            if "\x00" in value:
                raise ValueError("null bytes are not allowed")
            if len(value) > 200_000:
                raise ValueError("input exceeds the maximum allowed length")
        return value
