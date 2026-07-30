"""Create saved_searches table with tenant and user FKs

Revision ID: 000000000009
Revises: 000000000008
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "000000000009"
down_revision: str | None = "000000000008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
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
            ["tenant_id"], ["tenants.id"], name="fk_saved_searches_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_saved_searches_created_by", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_saved_searches"),
    )

    op.create_index("ix_saved_searches_tenant_id", "saved_searches", ["tenant_id"], unique=False)
    op.create_index("ix_saved_searches_created_by", "saved_searches", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_saved_searches_created_by", table_name="saved_searches")
    op.drop_index("ix_saved_searches_tenant_id", table_name="saved_searches")
    op.drop_table("saved_searches")
