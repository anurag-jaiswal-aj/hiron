"""add_embedding_failure_state

Revision ID: bbaa50acffef
Revises: 34afb76a4047
Create Date: 2026-09-16 15:41:25.567450

"""

from typing import Union
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = "bbaa50acffef"
down_revision: str | None = "34afb76a4047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add status nullable initially
    op.add_column("candidate_embeddings", sa.Column("status", sa.String(length=20), nullable=True))
    op.add_column("job_embeddings", sa.Column("status", sa.String(length=20), nullable=True))

    # 2. Backfill existing rows
    op.execute("UPDATE candidate_embeddings SET status = 'success' WHERE embedding IS NOT NULL")
    op.execute("UPDATE job_embeddings SET status = 'success' WHERE embedding IS NOT NULL")

    # 3. Make status NOT NULL
    op.alter_column(
        "candidate_embeddings",
        "status",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default="success",
    )
    op.alter_column(
        "job_embeddings",
        "status",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default="success",
    )

    # 4. Add error_type nullable
    op.add_column(
        "candidate_embeddings", sa.Column("error_type", sa.String(length=100), nullable=True)
    )
    op.add_column("job_embeddings", sa.Column("error_type", sa.String(length=100), nullable=True))

    # 5. Make embedding nullable
    op.alter_column(
        "candidate_embeddings",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=768),
        nullable=True,
    )
    op.alter_column(
        "job_embeddings",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=768),
        nullable=True,
    )


def downgrade() -> None:
    # 1. Clean up NULL embeddings
    op.execute("DELETE FROM candidate_embeddings WHERE embedding IS NULL")
    op.execute("DELETE FROM job_embeddings WHERE embedding IS NULL")

    # 2. Restore embedding to NOT NULL
    op.alter_column(
        "candidate_embeddings",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=768),
        nullable=False,
    )
    op.alter_column(
        "job_embeddings",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=768),
        nullable=False,
    )

    # 3. Drop columns
    op.drop_column("candidate_embeddings", "error_type")
    op.drop_column("job_embeddings", "error_type")
    op.drop_column("candidate_embeddings", "status")
    op.drop_column("job_embeddings", "status")
