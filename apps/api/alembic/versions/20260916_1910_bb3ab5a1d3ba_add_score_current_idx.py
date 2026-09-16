"""add_score_current_idx

Revision ID: bb3ab5a1d3ba
Revises: 'bbaa50acffef'
Create Date: 2026-09-16 19:10:06.448235

"""

from typing import Union
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bb3ab5a1d3ba"
down_revision: str | None = "bbaa50acffef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Safely demote existing duplicates keeping only the newest
    op.execute("""
        WITH duplicates AS (
            SELECT id,
                   ROW_NUMBER() OVER(PARTITION BY job_candidate_id ORDER BY created_at DESC) as rn
            FROM scores
            WHERE is_current = true
        )
        UPDATE scores
        SET is_current = false
        WHERE id IN (SELECT id FROM duplicates WHERE rn > 1);
    """)
    # 2. Add the partial unique index
    op.create_index(
        "uix_score_current",
        "scores",
        ["job_candidate_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uix_score_current", table_name="scores", postgresql_where=sa.text("is_current = true")
    )
