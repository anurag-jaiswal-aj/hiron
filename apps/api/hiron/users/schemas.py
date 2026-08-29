"""User management request and response Pydantic schemas per API Contract §Users."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from hiron.common.schemas import HironBaseModel

UserRole = Literal["org_admin", "recruiter", "hiring_manager"]


class UserResponse(HironBaseModel):
    """User profile response DTO per API Contract §USER-1 & USER-2."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    is_email_verified: bool
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserCreateRequest(HironBaseModel):
    """Request DTO for creating/inviting a user per API Contract §USER-3."""

    email: EmailStr = Field(..., description="User email address", max_length=320)
    full_name: str = Field(..., description="User full display name", min_length=1, max_length=200)
    role: UserRole = Field(..., description="Assigned tenant role")
    password: str | None = Field(
        default=None,
        description="Optional initial password (if omitted, a secure password is generated)",
        min_length=8,
        max_length=128,
    )


class UserUpdateRequest(HironBaseModel):
    """Request DTO for updating a user profile/role per API Contract §USER-4."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: UserRole | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class UserListResponse(HironBaseModel):
    """Paginated user list payload wrapper per API Contract §USER-1."""

    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class UserInvitationWebhookPayload(HironBaseModel):
    """Payload for QStash webhook delivering user invitations."""

    user_id: str = Field(..., description="Target User UUID")
    tenant_id: str = Field(..., description="Target Tenant UUID")
    email: str = Field(..., description="Target email address")


class AcceptInvitationRequest(HironBaseModel):
    """Payload for POST /api/v1/users/invite/accept."""

    token: str = Field(..., description="Raw invitation token", min_length=32)
    password: str = Field(..., description="New user password", min_length=8, max_length=320)
