"""Pydantic schemas for items."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemCreate(BaseModel):
    """Schema for creating a new item."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)

    @field_validator("name", mode="after")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace and validate not empty."""
        stripped = v.strip()
        if not stripped:
            msg = "Name cannot be empty or whitespace-only"
            raise ValueError(msg)
        return stripped


class ItemUpdate(BaseModel):
    """Schema for updating an item (partial update)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)

    @field_validator("name", mode="after")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        """Strip leading/trailing whitespace and validate not empty."""
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            msg = "Name cannot be empty or whitespace-only"
            raise ValueError(msg)
        return stripped


class ItemResponse(BaseModel):
    """Schema for item response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ItemList(BaseModel):
    """Schema for list of items with pagination info."""

    items: list[ItemResponse]
    total: int
    skip: int
    limit: int
