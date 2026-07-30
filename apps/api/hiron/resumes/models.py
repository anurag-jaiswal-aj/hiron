"""SQLAlchemy ORM models for Resume management per Database Design §5.6 & §5.7."""

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.candidates.models import Candidate
from hiron.common.models import BaseModel
from hiron.tenants.models import Tenant


class Resume(BaseModel):
    """SQLAlchemy model for parsed resume representation per Database Design §5.6."""

    __tablename__ = "resumes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", name="fk_resumes_tenant", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("candidates.id", name="fk_resumes_candidate", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="pending",
        nullable=False,
        default="pending",
    )
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(
        postgresql.JSONB,
        nullable=True,
    )
    parse_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    parser_model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    parse_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    raw_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    raw_text_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean(),
        server_default=text("false"),
        nullable=False,
        default=False,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    candidate: Mapped["Candidate"] = relationship("Candidate")
    file: Mapped["ResumeFile | None"] = relationship(
        "ResumeFile",
        back_populates="resume",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "uq_resumes_candidate_primary",
            "candidate_id",
            unique=True,
            postgresql_where=text("is_primary = TRUE"),
            sqlite_where=text("is_primary = TRUE"),
        ),
        Index("ix_resumes_tenant_status", "tenant_id", "status"),
        Index("ix_resumes_raw_text_hash", "tenant_id", "raw_text_hash"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'parsed', 'failed')",
            name="ck_resumes_status",
        ),
        CheckConstraint(
            "parse_confidence IS NULL OR (parse_confidence >= 0.0 AND parse_confidence <= 1.0)",
            name="ck_resumes_confidence_range",
        ),
    )


class ResumeFile(BaseModel):
    """SQLAlchemy model for uploaded original resume file metadata per Database Design §5.7."""

    __tablename__ = "resume_files"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", name="fk_resume_files_tenant", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("resumes.id", name="fk_resume_files_resume", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    s3_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="file")

    __table_args__ = (
        CheckConstraint(
            "content_type IN ('application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain')",
            name="ck_resume_files_content_type",
        ),
        CheckConstraint(
            "file_size_bytes > 0 AND file_size_bytes <= 10485760",
            name="ck_resume_files_size",
        ),
    )
