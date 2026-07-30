"""RefreshTokenRepository for async database data access per Database Design §5.3."""

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.tokens.models import RefreshToken


class RefreshTokenRepository:
    """Async SQLAlchemy repository executing database operations on RefreshToken entities.

    Per Database Design §5.3:
    - Lookup by token_hash (token refresh flow)
    - Revoke / Delete by user_id (session revocation on password change)
    - Delete WHERE expires_at < NOW() (daily cleanup job)
    """

    async def create(self, session: AsyncSession, token: RefreshToken) -> RefreshToken:
        """Persist a new RefreshToken entity."""
        session.add(token)
        await session.flush()
        return token

    async def get_by_token_hash(
        self,
        session: AsyncSession,
        token_hash: str,
    ) -> RefreshToken | None:
        """Fetch a RefreshToken by SHA-256 token_hash per Database Design §5.3."""
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash),
        )
        return result.scalar_one_or_none()

    async def revoke_by_token_hash(
        self,
        session: AsyncSession,
        token_hash: str,
    ) -> bool:
        """Revoke a refresh token by setting is_revoked = True per Database Design §5.3."""
        result = await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True),
        )
        cursor_result = cast(CursorResult[Any], result)
        return bool(cursor_result.rowcount > 0)

    async def revoke_all_for_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """Revoke all active refresh tokens for a user upon password change per Database Design §5.3."""
        result = await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True),
        )
        cursor_result = cast(CursorResult[Any], result)
        return int(cursor_result.rowcount)

    async def delete_expired(self, session: AsyncSession) -> int:
        """Delete tokens WHERE expires_at < NOW() for cleanup job per Database Design §5.3."""
        now = datetime.now(UTC)
        result = await session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < now),
        )
        cursor_result = cast(CursorResult[Any], result)
        return int(cursor_result.rowcount)
