"""Pydantic schemas for Audit Logs per API Contract §AUDIT-1..2."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditActorInfo(BaseModel):
    """Actor metadata embedded in audit log response."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    full_name: str = Field(..., serialization_alias="fullName")


class AuditLogData(BaseModel):
    """Audit log entry payload per API Contract §AUDIT-1."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    action: str = Field(...)
    entity_type: str = Field(..., serialization_alias="entityType")
    entity_id: uuid.UUID = Field(..., serialization_alias="entityId")
    actor: AuditActorInfo | None = Field(default=None)
    changes: dict[str, Any] | None = Field(default=None)
    ip_address: str | None = Field(default=None, serialization_alias="ipAddress")
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")


class AuditPagination(BaseModel):
    """Pagination metadata for audit queries."""

    model_config = ConfigDict(populate_by_name=True)

    has_more: bool = Field(..., serialization_alias="hasMore")
    next_cursor: str | None = Field(default=None, serialization_alias="nextCursor")
    total_count: int | None = Field(default=None, serialization_alias="totalCount")


class AuditLogListResponse(BaseModel):
    """Paginated audit logs response wrapper per §AUDIT-1."""

    data: list[AuditLogData] = Field(...)
    pagination: AuditPagination = Field(...)
