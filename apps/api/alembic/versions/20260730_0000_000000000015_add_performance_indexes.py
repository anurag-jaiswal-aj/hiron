"""Add performance covering indexes for candidate lists, job status filtering, and score distribution

Revision ID: 000000000015
Revises: 000000000014
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import alembic.op as op
import sqlalchemy as sa

revision: str = "000000000015"
down_revision: str | None = "000000000014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_candidates_tenant_created",
        "candidates",
        ["tenant_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_jobs_tenant_status",
        "jobs",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_job_candidates_tenant_job",
        "job_candidates",
        ["tenant_id", "job_id", "current_stage_id"],
        unique=False,
    )
    op.create_index(
        "ix_scores_current_fit_score",
        "scores",
        ["tenant_id", "is_current", sa.text("fit_score DESC")],
        unique=False,
        postgresql_where=sa.text("is_current = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("ix_scores_current_fit_score", table_name="scores")
    op.drop_index("ix_job_candidates_tenant_job", table_name="job_candidates")
    op.drop_index("ix_jobs_tenant_status", table_name="jobs")
    op.drop_index("ix_candidates_tenant_created", table_name="candidates")
