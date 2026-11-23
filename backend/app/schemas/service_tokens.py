"""Schemas for the admin service-token API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ServiceTokenCreateIn(BaseModel):
    """A new token's label and optional lifetime in days (omit for no expiry)."""

    name: str = Field(min_length=1, max_length=80)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class ServiceTokenOut(BaseModel):
    """A token on record. Never includes the token itself."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]


class ServiceTokenCreatedOut(BaseModel):
    """Returned once, at creation. ``token`` cannot be shown again."""

    token: str
    record: ServiceTokenOut
