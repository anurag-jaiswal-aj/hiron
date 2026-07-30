"""Authentication request and response Pydantic schemas per API Contract §6.1."""

import uuid

from pydantic import ConfigDict, EmailStr, Field

from hiron.common.schemas import HironBaseModel


class UserAuthPayload(HironBaseModel):
    """User profile summary data returned in authentication response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    tenant_id: uuid.UUID
    avatar_url: str | None = None


class LoginRequest(HironBaseModel):
    """Request payload for POST /api/v1/auth/login per API Contract §6.1."""

    email: EmailStr = Field(..., description="User email address", max_length=320)
    password: str = Field(..., description="Plain text password", min_length=1)
    tenant_id: uuid.UUID = Field(..., description="Tenant primary key UUID")


class LoginData(HironBaseModel):
    """Data payload for login success response per API Contract §6.1."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserAuthPayload


class RefreshTokenData(HironBaseModel):
    """Data payload for token refresh response per API Contract §6.1."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
