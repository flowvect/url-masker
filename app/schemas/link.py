"""Pydantic schemas for link creation, responses, and updates."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# ── Request schemas ───────────────────────────────────────────────────────

class LinkCreate(BaseModel):
    """Payload for creating a new short / masked link."""

    long_url: HttpUrl = Field(
        ..., description="The destination URL to shorten or mask."
    )
    custom_alias: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional custom short code (alphanumeric, hyphens, underscores).",
    )
    is_masked: bool = Field(
        False,
        description="If true, the short URL will cloak (proxy) the destination page.",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional UTC datetime after which the link becomes inactive.",
    )
    max_clicks: Optional[int] = Field(
        None, ge=1, description="Optional click cap — link deactivates after this many visits."
    )


class LinkUpdate(BaseModel):
    """Payload for patching an existing link."""

    custom_alias: Optional[str] = Field(None, min_length=3, max_length=50)
    is_masked: Optional[bool] = None
    expires_at: Optional[datetime] = None
    max_clicks: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


# ── Response schemas ──────────────────────────────────────────────────────

class LinkResponse(BaseModel):
    """Public representation of a link returned by the API."""

    id: uuid.UUID
    short_code: str
    short_url: str = Field(..., description="Full clickable short URL.")
    long_url: str
    is_masked: bool
    custom_alias: Optional[str]
    expires_at: Optional[datetime]
    max_clicks: Optional[int]
    click_count: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LinkListResponse(BaseModel):
    """Paginated list of links."""

    items: list[LinkResponse]
    total: int
