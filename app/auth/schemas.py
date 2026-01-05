"""Pydantic schemas for API key operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(..., min_length=1, max_length=255, description="Name for the key")
    client_id: str = Field(
        ..., min_length=1, max_length=255, description="Client identifier"
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp (NULL = never expires)",
    )

    @field_validator("name", "client_id", mode="after")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace and validate not empty."""
        stripped = v.strip()
        if not stripped:
            msg = "Value cannot be empty or whitespace-only"
            raise ValueError(msg)
        return stripped


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the actual key)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    client_id: str
    key_prefix: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class APIKeyCreated(BaseModel):
    """Schema returned when a new API key is created (includes the raw key)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    client_id: str
    key_prefix: str
    key: str = Field(
        ..., description="The API key - SAVE THIS, it will only be shown once!"
    )
    expires_at: datetime | None
    created_at: datetime


class APIKeyList(BaseModel):
    """Schema for listing API keys."""

    keys: list[APIKeyResponse]
    total: int
