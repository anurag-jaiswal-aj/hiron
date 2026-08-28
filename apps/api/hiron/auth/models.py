"""Authentication ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hiron.common.models import BaseModel


class PasswordResetToken(BaseModel):
    """Stores password reset tokens per Phase 10.3 requirements.

    Tokens are stored as SHA-256 hashes to prevent plaintext leakage.
    """

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_password_reset_tokens_user_id_users"),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_password_reset_tokens_token_hash", "token_hash", unique=True),
        Index("ix_password_reset_tokens_user_id", "user_id"),
    )
