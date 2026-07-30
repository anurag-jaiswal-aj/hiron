"""Create ai_usage_logs table with FKs, check constraints, and performance indexes

Revision ID: 000000000014
Revises: 000000000013
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import alembic.op as op
import sqlalchemy as sa

revision: str = "000000000014"
down_revision: str | None = "000000000013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("prompt_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=20), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_usd", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0.0"
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("is_cache_hit", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0",
            name="ck_ai_usage_logs_tokens",
        ),
        sa.CheckConstraint("cost_usd >= 0", name="ck_ai_usage_logs_cost"),
        sa.CheckConstraint(
            "status IN ('success', 'error', 'timeout', 'rate_limited')",
            name="ck_ai_usage_logs_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_ai_usage_logs_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ai_usage_logs_user", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_usage_logs"),
    )

    op.create_index(
        "ix_ai_usage_logs_tenant_created",
        "ai_usage_logs",
        ["tenant_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_ai_usage_logs_created_at", "ai_usage_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_ai_usage_logs_operation",
        "ai_usage_logs",
        ["operation", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_logs_operation", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_created_at", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_tenant_created", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
