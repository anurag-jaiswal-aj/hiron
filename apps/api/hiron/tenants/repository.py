"""TenantRepository for async database data access per Database Design §5.1."""

from datetime import datetime, timezone
from typing import Any, Sequence
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.tenants.models import Tenant


class TenantRepository:
    """Async SQLAlchemy repository executing database operations on Tenant entities.

    Per Database Design §5.1 & §9:
    - Lookup by id (on every request for RLS context)
    - Lookup by slug (for subdomain-based routing e.g. acme.hiron.ai)
    - List active tenants (filtered via partial index ix_tenants_is_active)
    - Update tenant attributes and settings
    - Hard delete (rare admin/GDPR teardown per §9)
    """

    async def create(self, session: AsyncSession, tenant: Tenant) -> Tenant:
        """Persist a new Tenant entity in the current session.

        Args:
            session: Active AsyncSession database handle.
            tenant: Unpersisted Tenant ORM instance.

        Returns:
            The created Tenant instance.
        """
        session.add(tenant)
        await session.flush()
        return tenant

    async def get_by_id(self, session: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
        """Fetch a Tenant entity by primary key ID per Database Design §5.1.

        Args:
            session: Active AsyncSession database handle.
            tenant_id: Tenant primary key UUID.

        Returns:
            Tenant entity if found, None otherwise.
        """
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, session: AsyncSession, slug: str) -> Tenant | None:
        """Fetch a Tenant entity by URL-safe subdomain slug per Database Design §5.1.

        Args:
            session: Active AsyncSession database handle.
            slug: Subdomain slug string (e.g. acme-corp).

        Returns:
            Tenant entity if found, None otherwise.
        """
        result = await session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def list_active(
        self,
        session: AsyncSession,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Tenant]:
        """List active tenants (is_active = True) per Database Design §5.1.

        Args:
            session: Active AsyncSession database handle.
            limit: Optional maximum rows to return.
            offset: Optional rows offset for pagination.

        Returns:
            Sequence of active Tenant entities.
        """
        stmt = select(Tenant).where(Tenant.is_active.is_(True))
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()

    async def update(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        **kwargs: Any,
    ) -> Tenant | None:
        """Update fields for an existing Tenant entity per Database Design §5.1.

        Args:
            session: Active AsyncSession database handle.
            tenant_id: Target tenant primary key UUID.
            **kwargs: Field name and value pairs to update.

        Returns:
            Updated Tenant entity if found, None otherwise.
        """
        if not kwargs:
            return await self.get_by_id(session, tenant_id)

        now = datetime.now(timezone.utc)
        kwargs["updated_at"] = now

        await session.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(**kwargs)
        )
        return await self.get_by_id(session, tenant_id)

    async def delete(self, session: AsyncSession, tenant_id: uuid.UUID) -> bool:
        """Hard-delete a Tenant entity per Database Design §9 (Hard delete admin/GDPR teardown).

        Args:
            session: Active AsyncSession database handle.
            tenant_id: Tenant primary key UUID to delete.

        Returns:
            True if a tenant row was deleted, False otherwise.
        """
        result = await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
        return result.rowcount > 0
