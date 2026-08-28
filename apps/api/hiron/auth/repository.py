"""Repository for Password Reset Tokens."""

from typing import Any, cast
import uuid
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, UTC

from hiron.auth.models import PasswordResetToken


class PasswordResetTokenRepository:
    """Async SQLAlchemy repository for PasswordResetToken entities."""

    async def create(self, session: AsyncSession, token: PasswordResetToken) -> PasswordResetToken:
        """Persist a new PasswordResetToken entity."""
        session.add(token)
        await session.flush()
        return token

    async def get_by_token_hash(
        self,
        session: AsyncSession,
        token_hash: str,
    ) -> PasswordResetToken | None:
        """Fetch a PasswordResetToken by SHA-256 token_hash."""
        result = await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(
        self,
        session: AsyncSession,
        token_hash: str,
    ) -> bool:
        """Atomically mark a token as used."""
        result = await session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None)
            )
            .values(used_at=datetime.now(UTC))
        )
        cursor_result = cast(CursorResult[Any], result)
        return bool(cursor_result.rowcount > 0)
