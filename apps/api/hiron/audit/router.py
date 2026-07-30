"""Thin FastAPI router for Audit Logs per API Contract §AUDIT-1..2."""

import datetime
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.audit.schemas import AuditLogListResponse
from hiron.audit.service import AuditService
from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.users.models import User

router = APIRouter(tags=["Audit Logs"])


def get_audit_service() -> AuditService:
    """Dependency provider for AuditService."""
    return AuditService()


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Audit Logs (AUDIT-1)",
)
async def list_audit_logs_endpoint(
    entity_type: str | None = Query(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(default=None, alias="entityId"),
    actor_id: uuid.UUID | None = Query(default=None, alias="actorId"),
    action: str | None = Query(default=None),
    start_date: datetime.datetime | None = Query(default=None, alias="startDate"),
    end_date: datetime.datetime | None = Query(default=None, alias="endDate"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: AuditService = Depends(get_audit_service),
) -> AuditLogListResponse:
    """Query immutable audit logs with multi-field filtering and RBAC scoping per §AUDIT-1."""
    return await service.list_audit_logs(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/audit-logs/entity/{entity_type}/{entity_id}",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Audit Log for Entity (AUDIT-2)",
)
async def get_entity_audit_logs_endpoint(
    entity_type: str,
    entity_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: AuditService = Depends(get_audit_service),
) -> AuditLogListResponse:
    """Get complete audit trail for a specific entity per §AUDIT-2."""
    return await service.get_entity_audit_logs(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
