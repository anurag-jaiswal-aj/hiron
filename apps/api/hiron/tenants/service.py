"""Tenant service providing organization management and tenant lifecycle business logic."""

import uuid
from collections.abc import Sequence
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.audit.service import AuditService
from hiron.audit.utils import extract_model_changes, sanitize_audit_payload
from hiron.common.exceptions import HironException
from hiron.tenants.models import Tenant
from hiron.tenants.repository import TenantRepository

logger = structlog.get_logger("hiron.api.tenants.service")

ALLOWED_PLANS = {"starter", "professional", "enterprise"}


class TenantNotFoundError(HironException):
    """Raised when a tenant entity is not found."""

    def __init__(self, message: str = "Tenant organization not found") -> None:
        super().__init__(
            message=message,
            code="TENANT_NOT_FOUND",
            status_code=404,
        )


class TenantSlugAlreadyExistsError(HironException):
    """Raised when creating or updating a tenant with a duplicate subdomain slug."""

    def __init__(self, slug: str) -> None:
        super().__init__(
            message=f"Tenant subdomain slug '{slug}' is already taken",
            code="SLUG_ALREADY_EXISTS",
            status_code=409,
        )


class InvalidTenantPlanError(HironException):
    """Raised when an invalid subscription plan is specified."""

    def __init__(self, plan: str) -> None:
        super().__init__(
            message=f"Invalid subscription plan '{plan}'. Allowed plans: starter, professional, enterprise",
            code="INVALID_TENANT_PLAN",
            status_code=400,
        )


class TenantService:
    """Core tenant business logic and repository orchestration service."""

    def __init__(
        self,
        tenant_repo: TenantRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        """Initialize TenantService with injected TenantRepository."""
        self.tenant_repo = tenant_repo or TenantRepository()
        self.audit_service = audit_service or AuditService()

    async def create_tenant(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        slug: str,
        plan: str = "starter",
        settings: dict[str, Any] | None = None,
    ) -> Tenant:
        """Create a new tenant organization per Database Design §5.1.

        Args:
            session: Active AsyncSession database handle.
            name: Display name for the organization.
            slug: URL-safe subdomain slug string.
            plan: Subscription plan string ('starter', 'professional', 'enterprise').
            settings: Optional JSONB configuration dictionary.

        Returns:
            Created Tenant entity.

        Raises:
            InvalidTenantPlanError: If plan is not an allowed subscription tier.
            TenantSlugAlreadyExistsError: If slug is already taken by another tenant.
        """
        plan_lower = plan.lower()
        if plan_lower not in ALLOWED_PLANS:
            raise InvalidTenantPlanError(plan)

        slug_lower = slug.lower().strip()
        existing = await self.tenant_repo.get_by_slug(session, slug_lower)
        if existing:
            raise TenantSlugAlreadyExistsError(slug_lower)

        tenant = Tenant(
            name=name,
            slug=slug_lower,
            plan=plan_lower,
            settings=settings or {},
            is_active=True,
        )
        created = await self.tenant_repo.create(session, tenant)
        logger.info("Tenant created successfully", tenant_id=str(created.id), slug=created.slug)

        changes = extract_model_changes(created, "create")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=created.id,
                action="tenant_created",
                entity_type="tenant",
                entity_id=created.id,
                actor_id=user_id,
                changes=changes,
            )

        await session.commit()
        return created

    async def get_tenant_by_id(self, session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
        """Fetch tenant by primary key UUID or raise TenantNotFoundError."""
        tenant = await self.tenant_repo.get_by_id(session, tenant_id)
        if not tenant:
            raise TenantNotFoundError()
        return tenant

    async def get_tenant_by_slug(self, session: AsyncSession, slug: str) -> Tenant:
        """Fetch tenant by URL-safe subdomain slug or raise TenantNotFoundError."""
        slug_lower = slug.lower().strip()
        tenant = await self.tenant_repo.get_by_slug(session, slug_lower)
        if not tenant:
            raise TenantNotFoundError()
        return tenant

    async def list_active_tenants(
        self,
        session: AsyncSession,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Tenant]:
        """List all active tenants for administrative management."""
        return await self.tenant_repo.list_active(session, limit=limit, offset=offset)

    async def update_tenant(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
        slug: str | None = None,
        plan: str | None = None,
        settings: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> Tenant:
        """Update existing tenant attributes per Database Design §5.1.

        Args:
            session: Active AsyncSession database handle.
            tenant_id: Target tenant primary key UUID.
            name: Optional new display name.
            slug: Optional new subdomain slug.
            plan: Optional new subscription plan.
            settings: Optional new JSONB settings dict.
            is_active: Optional active/inactive status toggle.

        Returns:
            Updated Tenant entity.

        Raises:
            TenantNotFoundError: If target tenant does not exist.
            InvalidTenantPlanError: If plan string is invalid.
            TenantSlugAlreadyExistsError: If updated slug belongs to another tenant.
        """
        tenant = await self.get_tenant_by_id(session, tenant_id)

        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if slug is not None:
            slug_lower = slug.lower().strip()
            existing = await self.tenant_repo.get_by_slug(session, slug_lower)
            if existing and existing.id != tenant_id:
                raise TenantSlugAlreadyExistsError(slug_lower)
            updates["slug"] = slug_lower
        if plan is not None:
            plan_lower = plan.lower()
            if plan_lower not in ALLOWED_PLANS:
                raise InvalidTenantPlanError(plan)
            updates["plan"] = plan_lower
        if settings is not None:
            updates["settings"] = settings
        if is_active is not None:
            updates["is_active"] = is_active

        updated_tenant = await self.tenant_repo.update(session, tenant_id, **updates)
        if not updated_tenant:
            raise TenantNotFoundError()

        logger.info("Tenant updated successfully", tenant_id=str(tenant.id))

        changes = extract_model_changes(updated_tenant, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="tenant_updated",
                entity_type="tenant",
                entity_id=updated_tenant.id,
                actor_id=user_id,
                changes=changes,
            )

        await session.commit()
        return updated_tenant

    async def delete_tenant(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Hard-delete tenant organization per Database Design §9."""
        tenant = await self.get_tenant_by_id(session, tenant_id)

        changes = extract_model_changes(tenant, "delete")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="tenant_deleted",
                entity_type="tenant",
                entity_id=tenant.id,
                actor_id=user_id,
                changes=changes,
            )

        await self.tenant_repo.delete(session, tenant_id)
        logger.info("Tenant deleted successfully", tenant_id=str(tenant_id))
        await session.commit()
