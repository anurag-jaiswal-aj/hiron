"""Create candidate_embeddings and job_embeddings tables with pgvector HNSW indexes

Revision ID: 000000000007
Revises: 000000000006
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import alembic.op as op
import pgvector.sqlalchemy
import sqlalchemy as sa

revision: str = "000000000007"
down_revision: str | None = "000000000006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create candidate_embeddings table
    op.create_table(
        "candidate_embeddings",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("source_text_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_candidate_embeddings_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_candidate_embeddings_candidate",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_embeddings"),
        sa.UniqueConstraint(
            "candidate_id", "model_version", name="uq_candidate_embeddings_candidate_model"
        ),
    )
    op.create_index(
        "ix_candidate_embeddings_tenant_id", "candidate_embeddings", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_candidate_embeddings_candidate_model",
        "candidate_embeddings",
        ["candidate_id", "model_version"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidate_embeddings_vector "
        "ON candidate_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )

    # 3. Create job_embeddings table
    op.create_table(
        "job_embeddings",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("source_text_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_job_embeddings_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name="fk_job_embeddings_job", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_embeddings"),
        sa.UniqueConstraint("job_id", "model_version", name="uq_job_embeddings_job_model"),
    )
    op.create_index("ix_job_embeddings_tenant_id", "job_embeddings", ["tenant_id"], unique=False)
    op.create_index(
        "ix_job_embeddings_job_model", "job_embeddings", ["job_id", "model_version"], unique=False
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_job_embeddings_vector "
        "ON job_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_job_embeddings_vector;")
    op.drop_index("ix_job_embeddings_job_model", table_name="job_embeddings")
    op.drop_index("ix_job_embeddings_tenant_id", table_name="job_embeddings")
    op.drop_table("job_embeddings")

    op.execute("DROP INDEX IF EXISTS ix_candidate_embeddings_vector;")
    op.drop_index("ix_candidate_embeddings_candidate_model", table_name="candidate_embeddings")
    op.drop_index("ix_candidate_embeddings_tenant_id", table_name="candidate_embeddings")
    op.drop_table("candidate_embeddings")
