"""User service providing user profile management, creation, updates, and role enforcement."""

import secrets
import uuid
from collections.abc import Sequence
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.common.exceptions import HironException
from hiron.core.security import hash_password
from hiron.tokens.repository import RefreshTokenRepository
from hiron.users.models import User
from hiron.users.repository import UserRepository

logger = structlog.get_logger("hiron.api.users.service")

ALLOWED_USER_ROLES = {"org_admin", "recruiter", "hiring_manager"}


class UserNotFoundError(HironException):
    """Raised when a target user is not found in the tenant."""

    def __init__(self, message: str = "User not found") -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
        )


class UserEmailAlreadyExistsError(HironException):
    """Raised when creating or updating a user with an email address already registered in the tenant."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message=f"User with email '{email}' already exists in this organization",
            code="RESOURCE_CONFLICT",
            status_code=409,
        )


class InvalidUserRoleError(HironException):
    """Raised when an invalid user role string is provided."""

    def __init__(self, role: str) -> None:
        super().__init__(
            message=f"Invalid user role '{role}'. Allowed roles: org_admin, recruiter, hiring_manager",
            code="INVALID_USER_ROLE",
            status_code=400,
        )


class LastAdminOperationError(HironException):
    """Raised when an operation would demote, deactivate, or delete the last org_admin."""

    def __init__(self, action_description: str = "operation") -> None:
        super().__init__(
            message=f"Cannot perform {action_description} on the last org_admin in the organization",
            code="RESOURCE_CONFLICT",
            status_code=409,
        )


class InsufficientUserPermissionsError(HironException):
    """Raised when a non-admin attempts unauthorized profile or role modifications."""

    def __init__(
        self, message: str = "Insufficient permissions to modify user profile or role"
    ) -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=403,
        )


class UserService:
    """Core user management business logic and repository orchestration service."""

    def __init__(
        self,
        user_repo: UserRepository | None = None,
        token_repo: RefreshTokenRepository | None = None,
    ) -> None:
        """Initialize UserService with injected repositories."""
        self.user_repo = user_repo or UserRepository()
        self.token_repo = token_repo or RefreshTokenRepository()

    async def list_users(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        role: str | None = None,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[User], int]:
        """List users for a tenant with optional filtering and pagination per API Contract §USER-1."""
        if role is not None and role not in ALLOWED_USER_ROLES:
            raise InvalidUserRoleError(role)

        return await self.user_repo.list_by_tenant(
            session=session,
            tenant_id=tenant_id,
            role=role,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> User:
        """Fetch user by ID and tenant_id or raise UserNotFoundError per API Contract §USER-2."""
        user = await self.user_repo.get_by_id_and_tenant(session, user_id, tenant_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def create_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        email: str,
        full_name: str,
        role: str,
        password: str | None = None,
    ) -> User:
        """Create/invite a new user in the tenant per API Contract §USER-3."""
        if role not in ALLOWED_USER_ROLES:
            raise InvalidUserRoleError(role)

        email_clean = email.lower().strip()
        existing = await self.user_repo.get_by_email_and_tenant(session, email_clean, tenant_id)
        if existing:
            raise UserEmailAlreadyExistsError(email_clean)

        raw_pwd = password if password else secrets.token_urlsafe(16)
        pwd_hash = hash_password(raw_pwd)

        user = User(
            tenant_id=tenant_id,
            email=email_clean,
            full_name=full_name.strip(),
            role=role,
            password_hash=pwd_hash,
            is_active=True,
            is_email_verified=False,
        )
        created = await self.user_repo.create(session, user)
        logger.info(
            "User created successfully",
            user_id=str(created.id),
            tenant_id=str(tenant_id),
            role=created.role,
        )
        return created

    async def _check_last_admin_protection(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        action: str,
    ) -> None:
        """Helper checking if active org_admin count is <= 1 before demoting, deactivating, or deleting."""
        active_admins = await self.user_repo.count_active_admins_by_tenant(session, tenant_id)
        if active_admins <= 1:
            raise LastAdminOperationError(action)

    def _validate_update_permissions(
        self,
        user_id: uuid.UUID,
        current_user_id: uuid.UUID,
        current_user_role: str,
        role: str | None,
        is_active: bool | None,
    ) -> None:
        """Verify role-based access permissions for user update operations."""
        is_admin = current_user_role == "org_admin"
        is_self = user_id == current_user_id

        if not is_admin and not is_self:
            raise InsufficientUserPermissionsError(
                "Non-admin users can only update their own profile"
            )

        if not is_admin and (role is not None or is_active is not None):
            raise InsufficientUserPermissionsError(
                "Only org_admin can change user roles or active status"
            )

    async def _build_user_updates(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user: User,
        full_name: str | None,
        role: str | None,
        is_active: bool | None,
    ) -> dict[str, Any]:
        """Build and validate update attribute dictionary."""
        updates: dict[str, Any] = {}

        if full_name is not None:
            updates["full_name"] = full_name.strip()

        if role is not None:
            if role not in ALLOWED_USER_ROLES:
                raise InvalidUserRoleError(role)
            if target_user.role == "org_admin" and role != "org_admin":
                await self._check_last_admin_protection(session, tenant_id, "demotion")
            updates["role"] = role

        if is_active is not None:
            if target_user.role == "org_admin" and not is_active and target_user.is_active:
                await self._check_last_admin_protection(session, tenant_id, "deactivation")
            updates["is_active"] = is_active
            if not is_active:
                await self.token_repo.revoke_all_for_user(session, user_id)

        return updates

    async def update_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_id: uuid.UUID,
        current_user_role: str,
        full_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> User:
        """Update user profile or role per API Contract §USER-4."""
        target_user = await self.get_user_by_id(session, user_id, tenant_id)

        self._validate_update_permissions(
            user_id, current_user_id, current_user_role, role, is_active
        )

        updates = await self._build_user_updates(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            target_user=target_user,
            full_name=full_name,
            role=role,
            is_active=is_active,
        )

        if not updates:
            return target_user

        updated = await self.user_repo.update(session, user_id, tenant_id, **updates)
        if not updated:
            raise UserNotFoundError()

        logger.info("User updated successfully", user_id=str(user_id), tenant_id=str(tenant_id))
        return updated

    async def deactivate_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_id: uuid.UUID,
        current_user_role: str,
    ) -> User:
        """Deactivate a user (soft delete) per API Contract §USER-5."""
        return await self.update_user(
            session=session,
            user_id=user_id,
            tenant_id=tenant_id,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
            is_active=False,
        )

    async def reactivate_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_id: uuid.UUID,
        current_user_role: str,
    ) -> User:
        """Reactivate a deactivated user per API Contract §USER-6."""
        return await self.update_user(
            session=session,
            user_id=user_id,
            tenant_id=tenant_id,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
            is_active=True,
        )

    async def delete_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_id: uuid.UUID,
        current_user_role: str,
    ) -> None:
        """Hard-delete user from organization."""
        if current_user_role != "org_admin":
            raise InsufficientUserPermissionsError("Only org_admin can delete users")

        target_user = await self.get_user_by_id(session, user_id, tenant_id)

        if target_user.role == "org_admin" and target_user.is_active:
            await self._check_last_admin_protection(session, tenant_id, "deletion")

        await self.token_repo.revoke_all_for_user(session, user_id)
        await self.user_repo.delete(session, user_id, tenant_id)
        logger.info(
            "User deleted successfully",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            deleted_by=str(current_user_id),
        )
