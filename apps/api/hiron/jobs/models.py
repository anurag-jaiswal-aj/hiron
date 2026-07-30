"""Job and PipelineStage SQLAlchemy ORM models per Database Design §5.4 & §5.8."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import BaseModel


class Job(BaseModel):
    """Job ORM model representing job descriptions / open roles per Database Design §5.4."""

    __tablename__ = "jobs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_jobs_tenant_id_tenants"),
        nullable=False,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", name="fk_jobs_created_by_users"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    employment_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    experience_years_min: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    experience_years_max: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    required_skills: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    preferred_skills: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    extracted_requirements: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'draft'"),
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    search_vector: Mapped[Any | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ORM relationships
    tenant: Mapped["Any | None"] = relationship("Tenant", foreign_keys=[tenant_id])
    creator: Mapped["Any | None"] = relationship("User", foreign_keys=[created_by])
    pipeline_stages: Mapped[list["PipelineStage"]] = relationship(
        "PipelineStage",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="PipelineStage.position",
    )

    __table_args__ = (
        # 1. Check Constraints (§5.4)
        CheckConstraint(
            "status IN ('draft', 'open', 'paused', 'closed', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "employment_type IN ('full_time', 'part_time', 'contract', 'internship') OR employment_type IS NULL",
            name="employment_type",
        ),
        CheckConstraint(
            "experience_years_max >= experience_years_min OR experience_years_max IS NULL OR experience_years_min IS NULL",
            name="experience_range",
        ),
        CheckConstraint(
            "experience_years_min >= 0 AND experience_years_min <= 50",
            name="experience_min_range",
        ),
        CheckConstraint(
            "experience_years_max >= 0 AND experience_years_max <= 50",
            name="experience_max_range",
        ),
        # 2. Indexes (§5.4)
        Index("ix_jobs_tenant_id", "tenant_id"),
        Index("ix_jobs_tenant_status", "tenant_id", "status"),
        Index(
            "ix_jobs_tenant_archived",
            "tenant_id",
            postgresql_where=text("is_archived = false"),
        ),
        Index(
            "ix_jobs_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_jobs_created_at",
            "tenant_id",
            text("created_at DESC"),
        ),
    )


class PipelineStage(BaseModel):
    """PipelineStage ORM model representing hiring pipeline stages per Database Design §5.8."""

    __tablename__ = "pipeline_stages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_pipeline_stages_tenant_id_tenants"),
        nullable=False,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE", name="fk_pipeline_stages_job_id_jobs"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    is_terminal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    stage_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'active'"),
    )

    # ORM relationships
    tenant: Mapped["Any | None"] = relationship("Tenant", foreign_keys=[tenant_id])
    job: Mapped["Job"] = relationship("Job", back_populates="pipeline_stages")

    __table_args__ = (
        # 1. Unique Constraints (§5.8)
        UniqueConstraint("job_id", "position", name="job_position"),
        UniqueConstraint("job_id", "name", name="job_name"),
        # 2. Check Constraints (§5.8)
        CheckConstraint(
            "position >= 1 AND position <= 20",
            name="position",
        ),
        CheckConstraint(
            "stage_type IN ('active', 'hired', 'rejected')",
            name="stage_type",
        ),
        # 3. Indexes (§5.8)
        Index("ix_pipeline_stages_job_id", "job_id", "position"),
        Index("ix_pipeline_stages_tenant_id", "tenant_id"),
    )
