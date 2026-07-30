"""SQLAlchemy model for candidate_tags table per Database Design §5.15."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import Base

if TYPE_CHECKING:
    from hiron.candidates.models import Candidate
    from hiron.tenants.models import Tenant
    from hiron.users.models import User


class CandidateTag(Base):
    """Lightweight tags attached to candidates for organization and filtering."""

    __tablename__ = "candidate_tags"
    __table_args__ = (
        UniqueConstraint("candidate_id", "tag_name", name="uq_candidate_tags_candidate_tag"),
    )

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
    tag_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tagged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant")
    candidate: Mapped["Candidate"] = relationship("Candidate")
    user: Mapped["User | None"] = relationship("User")
