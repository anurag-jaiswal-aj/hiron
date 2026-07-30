"""Create scores table with partial unique index, check constraints, and performance indexes

Revision ID: 000000000008
Revises: 000000000007
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "000000000008"
down_revision: str | None = "000000000007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scores",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("job_candidate_id", sa.UUID(), nullable=False),
        sa.Column("fit_score", sa.SmallInteger(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "skills_matched",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "skills_missing",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("prompt_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("fit_score >= 0 AND fit_score <= 100", name="ck_scores_fit_score_range"),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="ck_scores_confidence_range"
        ),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0", name="ck_scores_tokens_positive"
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_scores_latency_positive"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_scores_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["job_candidate_id"],
            ["job_candidates.id"],
            name="fk_scores_job_candidate",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scores"),
    )

    op.create_index("ix_scores_tenant_id", "scores", ["tenant_id"], unique=False)
    op.create_index("ix_scores_job_candidate_id", "scores", ["job_candidate_id"], unique=False)
    op.create_index(
        "ix_scores_current",
        "scores",
        ["job_candidate_id"],
        unique=False,
        postgresql_where=sa.text("is_current = TRUE"),
    )
    op.create_index(
        "ix_scores_fit_score",
        "scores",
        ["tenant_id", sa.text("fit_score DESC")],
        unique=False,
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_scores_job_candidate_current "
        "ON scores (job_candidate_id) WHERE is_current = TRUE;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_scores_job_candidate_current;")
    op.drop_index("ix_scores_fit_score", table_name="scores")
    op.drop_index("ix_scores_current", table_name="scores")
    op.drop_index("ix_scores_job_candidate_id", table_name="scores")
    op.drop_index("ix_scores_tenant_id", table_name="scores")
    op.drop_table("scores")
