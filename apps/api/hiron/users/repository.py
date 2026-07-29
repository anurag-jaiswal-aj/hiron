"""UserRepository for async database data access per Database Design §5.2."""

from typing import Sequence
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.users.models import User


class UserRepository:
    """Async SQLAlchemy repository executing database operations on User entities.
    
    Per Database Design §5.2:
    - Lookup by email (global user lookup)
    - Lookup by id + tenant_id (authentication context)
    - Lookup by email + tenant_id (tenant login flow)
    - List by tenant_id (team management)
    - Filter by role + tenant_id (role-based queries)
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
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id_and_tenant(
        self, session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> User | None:
        """Fetch a User entity by ID and tenant_id per Database Design §5.2."""
        result = await session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_tenant(
        self, session: AsyncSession, email: str, tenant_id: uuid.UUID
    ) -> User | None:
        """Fetch a User entity by email and tenant_id for tenant login per Database Design §5.2."""
        result = await session.execute(
            select(User).where(User.email == email, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[User]:
        """List users for a tenant per Database Design §5.2."""
        stmt = select(User).where(User.tenant_id == tenant_id)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
            
        result = await session.execute(stmt)
        return result.scalars().all()

    async def list_by_role_and_tenant(
        self, session: AsyncSession, role: str, tenant_id: uuid.UUID
    ) -> Sequence[User]:
        """Filter users by role and tenant_id per Database Design §5.2."""
        result = await session.execute(
            select(User).where(User.role == role, User.tenant_id == tenant_id)
        )
        return result.scalars().all()
