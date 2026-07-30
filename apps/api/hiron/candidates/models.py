"""SQLAlchemy ORM models for Candidate Management per Database Design §5.5 & §5.9."""

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import BaseModel
from hiron.jobs.models import Job, PipelineStage
from hiron.tenants.models import Tenant
from hiron.users.models import User


class Candidate(BaseModel):
    """SQLAlchemy model representing a Candidate profile per Database Design §5.5."""

    __tablename__ = "candidates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", name="fk_candidates_tenant", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
    )
    skills: Mapped[list[str]] = mapped_column(
        postgresql.JSONB(astext_type=Text()),
        server_default=text("'[]'::jsonb"),
        nullable=False,
        default=list,
    )
    total_experience_years: Mapped[int | None] = mapped_column(
        SmallInteger(),
        nullable=True,
    )
    current_title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    current_company: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        server_default="upload",
        nullable=False,
        default="upload",
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean(),
        server_default=text("false"),
        nullable=False,
        default=False,
    )
    search_vector: Mapped[Any | None] = mapped_column(
        postgresql.TSVECTOR(),
        nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="candidates")
    job_associations: Mapped[list["JobCandidate"]] = relationship(
        "JobCandidate",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "uq_candidates_tenant_email",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
            sqlite_where=text("email IS NOT NULL"),
        ),
        Index("ix_candidates_tenant_email", "tenant_id", "email"),
        Index("ix_candidates_tenant_name", "tenant_id", "full_name"),
        Index(
            "ix_candidates_tenant_archived",
            "tenant_id",
            postgresql_where=text("is_archived = FALSE"),
            sqlite_where=text("is_archived = FALSE"),
        ),
        CheckConstraint(
            "source IN ('upload', 'bulk_upload', 'api', 'ats_sync')",
            name="ck_candidates_source",
        ),
        CheckConstraint(
            "total_experience_years IS NULL OR (total_experience_years >= 0 AND total_experience_years <= 70)",
            name="ck_candidates_experience_range",
        ),
    )


class JobCandidate(BaseModel):
    """SQLAlchemy junction model connecting Candidates to Jobs per Database Design §5.9."""

    __tablename__ = "job_candidates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", name="fk_job_candidates_tenant", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("jobs.id", name="fk_job_candidates_job", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("candidates.id", name="fk_job_candidates_candidate", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_stage_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("pipeline_stages.id", name="fk_job_candidates_stage", ondelete="RESTRICT"),
        nullable=False,
    )
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_job_candidates_added_by", ondelete="SET NULL"),
        nullable=True,
    )
    is_shortlisted: Mapped[bool] = mapped_column(
        Boolean(),
        server_default=text("false"),
        nullable=False,
        default=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean(),
        server_default=text("false"),
        nullable=False,
        default=False,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    job: Mapped["Job"] = relationship("Job")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="job_associations")
    current_stage: Mapped["PipelineStage"] = relationship("PipelineStage")
    added_by_user: Mapped["User | None"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidates_job_candidate"),
        Index("ix_job_candidates_job_stage", "job_id", "current_stage_id"),
        Index(
            "ix_job_candidates_shortlisted",
            "job_id",
            postgresql_where=text("is_shortlisted = TRUE"),
            sqlite_where=text("is_shortlisted = TRUE"),
        ),
    )
