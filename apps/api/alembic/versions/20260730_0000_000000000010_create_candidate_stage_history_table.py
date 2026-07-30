"""Create candidate_stage_history table with FKs and performance indexes

Revision ID: 000000000010
Revises: 000000000009
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import alembic.op as op
import sqlalchemy as sa

revision: str = "000000000010"
down_revision: str | None = "000000000009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_stage_history",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("job_candidate_id", sa.UUID(), nullable=False),
        sa.Column("from_stage_id", sa.UUID(), nullable=True),
        sa.Column("to_stage_id", sa.UUID(), nullable=False),
        sa.Column("moved_by", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_csh_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["job_candidate_id"],
            ["job_candidates.id"],
            name="fk_csh_job_candidate",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_stage_id"], ["pipeline_stages.id"], name="fk_csh_from_stage", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["to_stage_id"], ["pipeline_stages.id"], name="fk_csh_to_stage", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["moved_by"], ["users.id"], name="fk_csh_moved_by", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_stage_history"),
    )

    op.create_index("ix_csh_tenant_id", "candidate_stage_history", ["tenant_id"], unique=False)
    op.create_index(
        "ix_csh_job_candidate_id",
        "candidate_stage_history",
        ["job_candidate_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_csh_created_at",
        "candidate_stage_history",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_csh_created_at", table_name="candidate_stage_history")
    op.drop_index("ix_csh_job_candidate_id", table_name="candidate_stage_history")
    op.drop_index("ix_csh_tenant_id", table_name="candidate_stage_history")
    op.drop_table("candidate_stage_history")
