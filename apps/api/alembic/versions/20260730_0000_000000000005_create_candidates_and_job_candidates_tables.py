"""create_candidates_and_job_candidates_tables

Revision ID: 000000000005
Revises: 000000000004
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000005"
down_revision: str | None = "000000000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create candidates and job_candidates tables with constraints, triggers, and indexes per Database Design §5.5 & §5.9."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Create candidates table
    op.create_table(
        "candidates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=True,
        ),
        sa.Column(
            "full_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "phone",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "location",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "linkedin_url",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "total_experience_years",
            sa.SmallInteger(),
            nullable=True,
        ),
        sa.Column(
            "current_title",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "current_company",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            server_default="upload",
            nullable=False,
        ),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_candidates_tenant",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "source IN ('upload', 'bulk_upload', 'api', 'ats_sync')",
            name="ck_candidates_source",
        ),
        sa.CheckConstraint(
            "total_experience_years IS NULL OR (total_experience_years >= 0 AND total_experience_years <= 70)",
            name="ck_candidates_experience_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidates"),
    )

    # Partial unique index for email per tenant
    op.create_index(
        "uq_candidates_tenant_email",
        "candidates",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
        sqlite_where=sa.text("email IS NOT NULL"),
    )

    # Standard candidate indexes
    op.create_index("ix_candidates_tenant_id", "candidates", ["tenant_id"])
    op.create_index("ix_candidates_tenant_email", "candidates", ["tenant_id", "email"])
    op.create_index("ix_candidates_tenant_name", "candidates", ["tenant_id", "full_name"])
    op.create_index(
        "ix_candidates_tenant_archived",
        "candidates",
        ["tenant_id"],
        postgresql_where=sa.text("is_archived = FALSE"),
        sqlite_where=sa.text("is_archived = FALSE"),
    )
    op.create_index(
        "ix_candidates_created_at",
        "candidates",
        ["tenant_id", sa.text("created_at DESC")],
    )

    # PostgreSQL specific GIN indexes & triggers
    if is_postgres:
        op.create_index(
            "ix_candidates_search_vector",
            "candidates",
            ["search_vector"],
            postgresql_using="gin",
        )
        op.create_index(
            "ix_candidates_skills",
            "candidates",
            ["skills"],
            postgresql_using="gin",
        )

        op.execute(
            """
            CREATE OR REPLACE FUNCTION candidates_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('english', coalesce(NEW.full_name, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(NEW.current_title, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(NEW.current_company, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(NEW.skills::text, '')), 'C');
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
            """
        )

        op.execute(
            """
            CREATE TRIGGER trg_candidates_search_vector
            BEFORE INSERT OR UPDATE ON candidates
            FOR EACH ROW EXECUTE FUNCTION candidates_search_vector_update();
            """
        )

    # 2. Create job_candidates junction table
    op.create_table(
        "job_candidates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "current_stage_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "added_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "is_shortlisted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "rejection_reason",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_job_candidates_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_candidates_job",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_job_candidates_candidate",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["current_stage_id"],
            ["pipeline_stages.id"],
            name="fk_job_candidates_stage",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name="fk_job_candidates_added_by",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_candidates_job_candidate"),
        sa.PrimaryKeyConstraint("id", name="pk_job_candidates"),
    )

    # Job candidates indexes
    op.create_index("ix_job_candidates_tenant_id", "job_candidates", ["tenant_id"])
    op.create_index("ix_job_candidates_job_id", "job_candidates", ["job_id"])
    op.create_index("ix_job_candidates_candidate_id", "job_candidates", ["candidate_id"])
    op.create_index(
        "ix_job_candidates_job_stage",
        "job_candidates",
        ["job_id", "current_stage_id"],
    )
    op.create_index(
        "ix_job_candidates_shortlisted",
        "job_candidates",
        ["job_id"],
        postgresql_where=sa.text("is_shortlisted = TRUE"),
        sqlite_where=sa.text("is_shortlisted = TRUE"),
    )


def downgrade() -> None:
    """Drop candidates and job_candidates tables, triggers, and indexes."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP TRIGGER IF EXISTS trg_candidates_search_vector ON candidates;")
        op.execute("DROP FUNCTION IF EXISTS candidates_search_vector_update();")

    op.drop_index("ix_job_candidates_shortlisted", table_name="job_candidates")
    op.drop_index("ix_job_candidates_job_stage", table_name="job_candidates")
    op.drop_index("ix_job_candidates_candidate_id", table_name="job_candidates")
    op.drop_index("ix_job_candidates_job_id", table_name="job_candidates")
    op.drop_index("ix_job_candidates_tenant_id", table_name="job_candidates")
    op.drop_table("job_candidates")

    if is_postgres:
        op.drop_index("ix_candidates_skills", table_name="candidates")
        op.drop_index("ix_candidates_search_vector", table_name="candidates")

    op.drop_index("ix_candidates_created_at", table_name="candidates")
    op.drop_index("ix_candidates_tenant_archived", table_name="candidates")
    op.drop_index("ix_candidates_tenant_name", table_name="candidates")
    op.drop_index("ix_candidates_tenant_email", table_name="candidates")
    op.drop_index("ix_candidates_tenant_id", table_name="candidates")
    op.drop_index("uq_candidates_tenant_email", table_name="candidates")
    op.drop_table("candidates")
