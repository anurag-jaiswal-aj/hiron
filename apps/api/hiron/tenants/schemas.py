"""Tenant request and response Pydantic schemas per API Contract."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from hiron.common.schemas import HironBaseModel


class TenantCreateRequest(HironBaseModel):
    """Request payload for creating a new tenant organization."""

    name: str = Field(..., description="Organization display name", min_length=1, max_length=200)
    slug: str = Field(..., description="URL-safe subdomain slug", min_length=1, max_length=63)
    plan: str = Field("starter", description="Subscription plan: starter, professional, enterprise")
    settings: dict[str, Any] | None = Field(
        default=None, description="Optional tenant JSONB configuration settings"
    )


class TenantUpdateRequest(HironBaseModel):
    """Request payload for updating an existing tenant organization."""

    name: str | None = Field(
        None, description="Organization display name", min_length=1, max_length=200
    )
    slug: str | None = Field(
        None, description="URL-safe subdomain slug", min_length=1, max_length=63
    )
    plan: str | None = Field(
        None, description="Subscription plan: starter, professional, enterprise"
    )
    settings: dict[str, Any] | None = Field(
        None, description="Optional tenant JSONB configuration settings"
    )
    is_active: bool | None = Field(None, description="Active status toggle")


class TenantResponse(HironBaseModel):
    """Response payload representing a Tenant organization."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    settings: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
