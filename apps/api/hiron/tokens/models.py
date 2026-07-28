"""RefreshToken SQLAlchemy ORM model definition per Database Design §5.3."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hiron.common.models import BaseModel


class RefreshToken(BaseModel):
    """Tracks active JWT refresh tokens for single-use rotation and session revocation.
    
    Per Database Design §5.3:
    - id: UUID primary key (inherited from BaseModel)
    - user_id: FK -> users.id (ON DELETE CASCADE)
    - tenant_id: FK -> tenants.id (ON DELETE CASCADE, denormalized for RLS)
    - token_hash: SHA-256 hash of the refresh token (VARCHAR 64)
    - expires_at: Token expiration timestamp (TIMESTAMPTZ)
    - is_revoked: Explicit revocation flag (password change, logout)
    - user_agent: Optional browser/device info for session UI
    - ip_address: Optional IP address at token issuance (INET)
    - created_at, updated_at: Audit timestamps (inherited from BaseModel)
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_refresh_tokens_user_id_users"),
        nullable=False,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_refresh_tokens_tenant_id_tenants"),
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

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
    )

    __table_args__ = (
        # 1. Unique Constraints (§5.3)
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        # 2. Indexes (§5.3)
        Index("ix_refresh_tokens_token_hash", "token_hash"),
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )
