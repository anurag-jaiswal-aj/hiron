"""SQLAlchemy models for candidate_embeddings and job_embeddings tables per Database Design §5.11-5.12."""

import datetime
import uuid
from typing import TYPE_CHECKING

import pgvector.sqlalchemy
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import Base

if TYPE_CHECKING:
    from hiron.candidates.models import Candidate
    from hiron.jobs.models import Job
    from hiron.tenants.models import Tenant


class CandidateEmbedding(Base):
    """Stores 768-dimensional vector embeddings for candidate resume text."""

    __tablename__ = "candidate_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "model_version", name="uq_candidate_embeddings_candidate_model"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(pgvector.sqlalchemy.Vector(768), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant")
    candidate: Mapped["Candidate"] = relationship("Candidate")


class JobEmbedding(Base):
    """Stores 768-dimensional vector embeddings for job description text."""

    __tablename__ = "job_embeddings"
    __table_args__ = (
        UniqueConstraint("job_id", "model_version", name="uq_job_embeddings_job_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(pgvector.sqlalchemy.Vector(768), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant")
    job: Mapped["Job"] = relationship("Job")
