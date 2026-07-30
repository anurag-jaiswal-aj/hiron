"""SQLAlchemy model for scores table per Database Design §5.10."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import Base

if TYPE_CHECKING:
    from hiron.candidates.models import JobCandidate
    from hiron.tenants.models import Tenant


class Score(Base):
    """Stores AI fit scores, dimensional breakdowns, explanations, and provenance."""

    __tablename__ = "scores"
    __table_args__ = (
        CheckConstraint("fit_score >= 0 AND fit_score <= 100", name="ck_scores_fit_score_range"),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="ck_scores_confidence_range"
        ),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0", name="ck_scores_tokens_positive"
        ),
        CheckConstraint("latency_ms >= 0", name="ck_scores_latency_positive"),
    )

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
    fit_score: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    confidence: Mapped[float] = mapped_column(Float(), nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB(astext_type=Text()), nullable=False)
    explanation: Mapped[str] = mapped_column(Text(), nullable=False)
    skills_matched: Mapped[list[str]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default=text("'[]'::jsonb"), default=list
    )
    skills_missing: Mapped[list[str]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default=text("'[]'::jsonb"), default=list
    )
    prompt_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default=text("'[]'::jsonb"), default=list
    )
    is_current: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant")
    job_candidate: Mapped["JobCandidate"] = relationship("JobCandidate")
