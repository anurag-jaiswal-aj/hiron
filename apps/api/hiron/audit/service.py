"""Audit service managing RBAC authorization, audit log recording, and filterable log queries per API Contract §AUDIT-1..2."""

import datetime
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.audit.exceptions import InsufficientAuditPermissionsError
from hiron.audit.models import AuditLog
from hiron.audit.repository import AuditRepository
from hiron.audit.schemas import (
    AuditActorInfo,
    AuditLogData,
    AuditLogListResponse,
    AuditPagination,
)

logger = structlog.get_logger("hiron.audit.service")


class AuditService:
    """Business service handling audit log queries, RBAC scoping, and event record creation."""

    def __init__(self, audit_repository: AuditRepository | None = None) -> None:
        self.audit_repo = audit_repository or AuditRepository()

    def _build_audit_data(self, log: AuditLog) -> AuditLogData:
        """Convert AuditLog ORM model to Pydantic AuditLogData schema."""
        actor_info = (
            AuditActorInfo(id=log.actor.id, full_name=log.actor.full_name) if log.actor else None
        )
        return AuditLogData(
            id=log.id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            actor=actor_info,
            changes=log.changes,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )

    async def list_audit_logs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> AuditLogListResponse:
        """Query audit logs with multi-field filtering and RBAC scoping per API Contract §AUDIT-1."""
        # Enforce RBAC: Recruiter sees own actions only unless filtering a specific entity
        effective_actor_id = actor_id
        if user_role != "org_admin":
            if user_role == "recruiter":
                if not entity_id:
                    effective_actor_id = user_id
            else:
                raise InsufficientAuditPermissionsError(
                    f"User with role '{user_role}' is not authorized to query audit logs"
                )

        items, has_more, next_cursor = await self.audit_repo.list_audit_logs(
            session=session,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=effective_actor_id,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            cursor=cursor,
        )

        logger.info(
            "Queried audit logs",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            returned_count=len(items),
            has_more=has_more,
        )

        return AuditLogListResponse(
            data=[self._build_audit_data(log) for log in items],
            pagination=AuditPagination(
                has_more=has_more,
                next_cursor=next_cursor,
                total_count=None,
            ),
        )

    async def get_entity_audit_logs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        entity_type: str,
        entity_id: uuid.UUID,
        limit: int = 50,
    ) -> AuditLogListResponse:
        """Fetch full audit timeline for a specific entity per API Contract §AUDIT-2."""
        if user_role not in ("org_admin", "recruiter"):
            raise InsufficientAuditPermissionsError(
                f"User with role '{user_role}' is not authorized to view entity audit trail"
            )

        logs = await self.audit_repo.get_audit_logs_for_entity(
            session=session,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

        return AuditLogListResponse(
            data=[self._build_audit_data(log) for log in logs],
            pagination=AuditPagination(has_more=False, next_cursor=None, total_count=len(logs)),
        )

    async def record_audit_log(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        changes: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Helper to create and persist an immutable audit log entry."""
        return await self.audit_repo.create_audit_log(
            session=session,
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
