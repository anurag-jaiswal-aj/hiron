"""SQLAlchemy model for candidate_stage_history table per Database Design §5.13."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import Base

if TYPE_CHECKING:
    from hiron.candidates.models import JobCandidate
    from hiron.jobs.models import PipelineStage
    from hiron.tenants.models import Tenant
    from hiron.users.models import User


class CandidateStageHistory(Base):
    """Immutable audit trail of candidate stage transitions in a job pipeline."""

    __tablename__ = "candidate_stage_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_stages.id", ondelete="SET NULL"), nullable=True
    )
    to_stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_stages.id", ondelete="RESTRICT"), nullable=False
    )
    moved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant")
    job_candidate: Mapped["JobCandidate"] = relationship("JobCandidate")
    from_stage: Mapped["PipelineStage | None"] = relationship(
        "PipelineStage", foreign_keys=[from_stage_id]
    )
    to_stage: Mapped["PipelineStage"] = relationship("PipelineStage", foreign_keys=[to_stage_id])
    actor: Mapped["User | None"] = relationship("User", foreign_keys=[moved_by])
