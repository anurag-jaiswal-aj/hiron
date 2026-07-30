"""SQLAlchemy model for ai_usage_logs table per Database Design §5.16."""

import datetime
import decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiron.common.models import Base

if TYPE_CHECKING:
    from hiron.tenants.models import Tenant
    from hiron.users.models import User


class AIUsageLog(Base):
    """Tracks every AI API call for cost monitoring, token accounting, and usage analytics per Database Design §5.16."""

    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0",
            name="ck_ai_usage_logs_tokens",
        ),
        CheckConstraint("cost_usd >= 0", name="ck_ai_usage_logs_cost"),
        CheckConstraint(
            "status IN ('success', 'error', 'timeout', 'rate_limited')",
            name="ck_ai_usage_logs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    cost_usd: Mapped[decimal.Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=decimal.Decimal("0.0")
    )
    latency_ms: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_cache_hit: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    tenant: Mapped["Tenant"] = relationship("Tenant")
    user: Mapped["User | None"] = relationship("User")
