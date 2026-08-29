"""UserRepository for async database data access per Database Design §5.2."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.users.models import User, UserInvitationToken


class UserRepository:
    """Async SQLAlchemy repository executing database operations on User entities.

    Per Database Design §5.2:
    - Lookup by email (global user lookup)
    - Lookup by id + tenant_id (authentication context & tenant isolation)
    - Lookup by email + tenant_id (tenant login flow)
    - List by tenant_id with role/is_active filters and pagination
    - Count active admins by tenant for last-admin safety check
    - Update user attributes & last_login_at timestamp
    - Delete user by primary key and tenant_id
    """

    async def create(self, session: AsyncSession, user: User) -> User:
        """Persist a new User entity in the current session."""
        session.add(user)
        await session.flush()
        return user

    async def get_by_id(self, session: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Fetch a User entity by primary key ID."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Fetch a User entity globally by email address."""
        result = await session.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()

    async def get_by_id_and_tenant(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> User | None:
        """Fetch a User entity by ID and tenant_id per Database Design §5.2."""
        result = await session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id),
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_tenant(
        self,
        session: AsyncSession,
        email: str,
        tenant_id: uuid.UUID,
    ) -> User | None:
        """Fetch a User entity by email and tenant_id for tenant login per Database Design §5.2."""
        result = await session.execute(
            select(User).where(User.email == email.lower().strip(), User.tenant_id == tenant_id),
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        role: str | None = None,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[User], int]:
        """Fetch paginated list of users and total count per Database Design §5.2."""
        conditions = [User.tenant_id == tenant_id]
        if role is not None:
            conditions.append(User.role == role)
        if is_active is not None:
            conditions.append(User.is_active.is_(is_active))

        count_stmt = select(func.count()).select_from(User).where(*conditions)
        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar_one()

        stmt = (
            select(User)
            .where(*conditions)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        users = result.scalars().all()
        return users, total_count

    async def list_by_role_and_tenant(
        self,
        session: AsyncSession,
        role: str,
        tenant_id: uuid.UUID,
    ) -> Sequence[User]:
        """Filter users by role and tenant_id per Database Design §5.2."""
        result = await session.execute(
            select(User).where(User.role == role, User.tenant_id == tenant_id),
        )
        return result.scalars().all()

    async def count_active_admins_by_tenant(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> int:
        """Count active org_admin users for a tenant to enforce last-admin protection."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(
                User.tenant_id == tenant_id,
                User.role == "org_admin",
                User.is_active.is_(True),
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def update(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        **kwargs: Any,
    ) -> User | None:
        """Update existing User entity attributes scoped by tenant_id."""
        kwargs["updated_at"] = datetime.now(UTC)
        await session.execute(
            update(User).where(User.id == user_id, User.tenant_id == tenant_id).values(**kwargs),
        )
        return await self.get_by_id_and_tenant(session, user_id, tenant_id)

    async def update_last_login(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        last_login_at: datetime | None = None,
    ) -> bool:
        """Update last_login_at timestamp for a User entity per Database Design §5.2."""
        now = last_login_at or datetime.now(UTC)
        result = await session.execute(
            update(User).where(User.id == user_id).values(last_login_at=now, updated_at=now),
        )
        cursor_result = cast(CursorResult[Any], result)
        return bool(cursor_result.rowcount > 0)

    async def delete(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Delete a User entity scoped by tenant_id."""
        result = await session.execute(
            delete(User).where(User.id == user_id, User.tenant_id == tenant_id),
        )
        cursor_result = cast(CursorResult[Any], result)
        return bool(cursor_result.rowcount > 0)


class UserInvitationTokenRepository:
    """Async SQLAlchemy repository for UserInvitationToken entities."""

    async def create(
        self, session: AsyncSession, token: UserInvitationToken
    ) -> UserInvitationToken:
        session.add(token)
        await session.flush()
        return token

    async def get_by_token_hash(
        self, session: AsyncSession, token_hash: str
    ) -> UserInvitationToken | None:
        result = await session.execute(
            select(UserInvitationToken).where(UserInvitationToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, session: AsyncSession, token_hash: str) -> bool:
        stmt = (
            update(UserInvitationToken)
            .where(
                UserInvitationToken.token_hash == token_hash,
                UserInvitationToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
        result = await session.execute(stmt)
        return cast(CursorResult[Any], result).rowcount > 0

    async def revoke_pending_for_user(self, session: AsyncSession, user_id: uuid.UUID) -> int:
        stmt = (
            delete(UserInvitationToken)
            .where(
                UserInvitationToken.user_id == user_id,
                UserInvitationToken.used_at.is_(None),
            )
        )
        result = await session.execute(stmt)
        return cast(CursorResult[Any], result).rowcount

    async def get_pending_for_user(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> Sequence[UserInvitationToken]:
        result = await session.execute(
            select(UserInvitationToken).where(
                UserInvitationToken.user_id == user_id,
                UserInvitationToken.used_at.is_(None),
            )
        )
        return result.scalars().all()
