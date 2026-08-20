"""migrate embedding vector dimensions to 768

Revision ID: 9e4f33bbb02c
Revises: 'd336f5d8940e'
Create Date: 2026-08-14 14:53:00.156469

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e4f33bbb02c"
down_revision: str | None = "d336f5d8940e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_candidate_embeddings_vector;")
    op.execute("DROP INDEX IF EXISTS ix_job_embeddings_vector;")

    op.execute("ALTER TABLE candidate_embeddings ALTER COLUMN embedding TYPE vector(768)")
    op.execute("ALTER TABLE job_embeddings ALTER COLUMN embedding TYPE vector(768)")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidate_embeddings_vector "
        "ON candidate_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_job_embeddings_vector "
        "ON job_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_candidate_embeddings_vector;")
    op.execute("DROP INDEX IF EXISTS ix_job_embeddings_vector;")

    op.execute("ALTER TABLE candidate_embeddings ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("ALTER TABLE job_embeddings ALTER COLUMN embedding TYPE vector(1536)")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidate_embeddings_vector "
        "ON candidate_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_job_embeddings_vector "
        "ON job_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )
