"""Create candidate_notes and candidate_tags tables with FKs, unique constraints, and indexes

Revision ID: 000000000011
Revises: 000000000010
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import alembic.op as op
import sqlalchemy as sa

revision: str = "000000000011"
down_revision: str | None = "000000000010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create candidate_notes table
    op.create_table(
        "candidate_notes",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_candidate_notes_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_candidate_notes_candidate",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_candidate_notes_author", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name="fk_candidate_notes_job", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_notes"),
    )

    op.create_index("ix_candidate_notes_tenant_id", "candidate_notes", ["tenant_id"], unique=False)
    op.create_index(
        "ix_candidate_notes_candidate_id",
        "candidate_notes",
        ["candidate_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_candidate_notes_author_id", "candidate_notes", ["author_id"], unique=False)

    # 2. Create candidate_tags table
    op.create_table(
        "candidate_tags",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("tag_name", sa.String(length=50), nullable=False),
        sa.Column("tagged_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_candidate_tags_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_candidate_tags_candidate",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tagged_by"], ["users.id"], name="fk_candidate_tags_tagged_by", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_tags"),
        sa.UniqueConstraint("candidate_id", "tag_name", name="uq_candidate_tags_candidate_tag"),
    )

    op.create_index("ix_candidate_tags_tenant_id", "candidate_tags", ["tenant_id"], unique=False)
    op.create_index(
        "ix_candidate_tags_candidate_id", "candidate_tags", ["candidate_id"], unique=False
    )
    op.create_index(
        "ix_candidate_tags_tenant_tag",
        "candidate_tags",
        ["tenant_id", "tag_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_tags_tenant_tag", table_name="candidate_tags")
    op.drop_index("ix_candidate_tags_candidate_id", table_name="candidate_tags")
    op.drop_index("ix_candidate_tags_tenant_id", table_name="candidate_tags")
    op.drop_table("candidate_tags")

    op.drop_index("ix_candidate_notes_author_id", table_name="candidate_notes")
    op.drop_index("ix_candidate_notes_candidate_id", table_name="candidate_notes")
    op.drop_index("ix_candidate_notes_tenant_id", table_name="candidate_notes")
    op.drop_table("candidate_notes")
