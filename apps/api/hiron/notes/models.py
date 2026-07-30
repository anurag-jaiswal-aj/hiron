"""SQLAlchemy model for candidate_notes table per Database Design §5.14."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import Base

if TYPE_CHECKING:
    from hiron.candidates.models import Candidate
    from hiron.jobs.models import Job
    from hiron.tenants.models import Tenant
    from hiron.users.models import User


class CandidateNote(Base):
    """Free-text notes attached to candidates with @mentions and privacy controls."""

    __tablename__ = "candidate_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant")
    candidate: Mapped["Candidate"] = relationship("Candidate")
    author: Mapped["User | None"] = relationship("User")
    job: Mapped["Job | None"] = relationship("Job")
