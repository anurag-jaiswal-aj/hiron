"""Audit log repository managing SQL persistence and query filtering per Database Design §5.17."""

import datetime
import uuid
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiron.audit.models import AuditLog
from hiron.common.pagination import decode_cursor, encode_cursor


class AuditRepository:
    """Repository handling SQL persistence for audit logs."""

    async def create_audit_log(
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
        """Insert an immutable audit log entry."""
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(audit_entry)
        await session.flush()
        return audit_entry

    async def list_audit_logs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[AuditLog], bool, str | None]:
        """Fetch audit log entries matching filters with cursor-based pagination."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .options(selectinload(AuditLog.actor))
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        )

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if start_date:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        if cursor:
            decoded = decode_cursor(cursor)
            cursor_dt = datetime.datetime.fromisoformat(decoded["dt"])
            cursor_id = uuid.UUID(decoded["id"])

            stmt = stmt.where(
                tuple_(AuditLog.created_at, AuditLog.id) < tuple_(cursor_dt, cursor_id)
            )

        stmt = stmt.limit(limit + 1)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = encode_cursor(
                {"dt": last_item.created_at.isoformat(), "id": str(last_item.id)}
            )

        return items, has_more, next_cursor

    async def get_audit_logs_for_entity(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Fetch all audit entries for a specific entity ordered by created_at DESC."""
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .options(selectinload(AuditLog.actor))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
