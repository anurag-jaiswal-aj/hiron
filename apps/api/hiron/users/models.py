"""User SQLAlchemy ORM model definition per Database Design §5.2."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hiron.common.models import BaseModel


class User(BaseModel):
    """Represents a human user (org_admin, recruiter, hiring_manager) across all tenants.
    
    Per Database Design §5.2:
    - id: UUID primary key (inherited from BaseModel)
    - tenant_id: FK -> tenants.id (ON DELETE CASCADE)
    - email: User email (320 chars per RFC 5321), unique within tenant
    - full_name: User display name
    - password_hash: Argon2id hash (nullable for OAuth-only users)
    - role: One of org_admin, recruiter, hiring_manager
    - avatar_url: Optional profile picture URL
    - is_active: Account active status flag
    - is_email_verified: Email verification flag
    - last_login_at: UTC timestamp of last successful authentication
    - created_at, updated_at: Audit timestamps (inherited from BaseModel)
    """

    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_users_tenant_id_tenants"),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    password_hash: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        # 1. Unique Constraints (§5.2)
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_id_email"),
        # 2. Check Constraints (§5.2)
        CheckConstraint(
            "role IN ('org_admin', 'recruiter', 'hiring_manager')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "email ~* '^[^@]+@[^@]+\\.[^@]+$'",
            name="ck_users_email_format",
        ),
        # 3. Indexes (§5.2)
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_tenant_id_email", "tenant_id", "email"),
        Index("ix_users_tenant_id_role", "tenant_id", "role"),
    )
