"""Tenant SQLAlchemy ORM model definition per Database Design §5.1."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import BaseModel

if TYPE_CHECKING:
    from hiron.candidates.models import Candidate


class Tenant(BaseModel):
    """Represents a customer organization. Root entity for multi-tenant data isolation per Database Design §5.1."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
    )

    plan: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'starter'"),
    )

    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    # Relationships
    candidates: Mapped[list["Candidate"]] = relationship(
        "Candidate", back_populates="tenant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # 1. Unique Constraints (§5.1)
        UniqueConstraint("slug", name="uq_tenants_slug"),
        # 2. Check Constraints (§5.1)
        CheckConstraint(
            "plan IN ('starter', 'professional', 'enterprise')",
            name="plan",
        ),
        CheckConstraint(
            "slug ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'",
            name="slug_format",
        ),
        # 3. Indexes (§5.1)
        Index("ix_tenants_slug", "slug"),
        Index("ix_tenants_is_active", "is_active", postgresql_where=text("is_active = true")),
    )
