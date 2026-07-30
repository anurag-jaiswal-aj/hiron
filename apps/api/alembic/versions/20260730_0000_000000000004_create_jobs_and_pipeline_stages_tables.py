"""create_jobs_and_pipeline_stages_tables

Revision ID: 000000000004
Revises: 000000000003
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000004"
down_revision: str | None = "000000000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create jobs and pipeline_stages tables with constraints, triggers, and indexes per Database Design §5.4 & §5.8."""
    # 1. Create jobs table
    op.create_table(
        "jobs",
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
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "department",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "location",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "employment_type",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "experience_years_min",
            sa.SmallInteger(),
            nullable=True,
        ),
        sa.Column(
            "experience_years_max",
            sa.SmallInteger(),
            nullable=True,
        ),
        sa.Column(
            "required_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "preferred_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "extracted_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'draft'"),
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
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_jobs_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_jobs_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.CheckConstraint(
            "status IN ('draft', 'open', 'paused', 'closed', 'archived')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint(
            "employment_type IN ('full_time', 'part_time', 'contract', 'internship') OR employment_type IS NULL",
            name="ck_jobs_employment_type",
        ),
        sa.CheckConstraint(
            "experience_years_max >= experience_years_min OR experience_years_max IS NULL OR experience_years_min IS NULL",
            name="ck_jobs_experience_range",
        ),
        sa.CheckConstraint(
            "experience_years_min >= 0 AND experience_years_min <= 50",
            name="ck_jobs_experience_min_range",
        ),
        sa.CheckConstraint(
            "experience_years_max >= 0 AND experience_years_max <= 50",
            name="ck_jobs_experience_max_range",
        ),
    )

    # Create indexes for jobs table (§5.4)
    op.create_index("ix_jobs_tenant_id", "jobs", ["tenant_id"], unique=False)
    op.create_index("ix_jobs_tenant_status", "jobs", ["tenant_id", "status"], unique=False)
    op.create_index(
        "ix_jobs_tenant_archived",
        "jobs",
        ["tenant_id"],
        unique=False,
        postgresql_where=sa.text("is_archived = false"),
    )
    op.create_index(
        "ix_jobs_search_vector",
        "jobs",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_jobs_created_at",
        "jobs",
        ["tenant_id", sa.text("created_at DESC")],
        unique=False,
    )

    # Create full-text search trigger function and trigger for jobs (§5.4 & §14)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION jobs_generate_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_jobs_search_vector_update
            BEFORE INSERT OR UPDATE OF title, description ON jobs
            FOR EACH ROW EXECUTE FUNCTION jobs_generate_search_vector();
        """
    )

    # 2. Create pipeline_stages table (§5.8)
    op.create_table(
        "pipeline_stages",
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
            "name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.SmallInteger(),
            nullable=False,
        ),
        sa.Column(
            "is_terminal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "stage_type",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pipeline_stages_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_pipeline_stages_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pipeline_stages"),
        sa.UniqueConstraint("job_id", "position", name="uq_pipeline_stages_job_position"),
        sa.UniqueConstraint("job_id", "name", name="uq_pipeline_stages_job_name"),
        sa.CheckConstraint(
            "position >= 1 AND position <= 20",
            name="ck_pipeline_stages_position",
        ),
        sa.CheckConstraint(
            "stage_type IN ('active', 'hired', 'rejected')",
            name="ck_pipeline_stages_stage_type",
        ),
    )

    # Create indexes for pipeline_stages (§5.8)
    op.create_index(
        "ix_pipeline_stages_job_id", "pipeline_stages", ["job_id", "position"], unique=False
    )
    op.create_index("ix_pipeline_stages_tenant_id", "pipeline_stages", ["tenant_id"], unique=False)


def downgrade() -> None:
    """Drop pipeline_stages and jobs tables, associated triggers, and indexes."""
    # Drop pipeline_stages table & indexes
    op.drop_index("ix_pipeline_stages_tenant_id", table_name="pipeline_stages")
    op.drop_index("ix_pipeline_stages_job_id", table_name="pipeline_stages")
    op.drop_table("pipeline_stages")

    # Drop jobs trigger & trigger function
    op.execute("DROP TRIGGER IF EXISTS trg_jobs_search_vector_update ON jobs;")
    op.execute("DROP FUNCTION IF EXISTS jobs_generate_search_vector();")

    # Drop jobs table & indexes
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_search_vector", table_name="jobs")
    op.drop_index("ix_jobs_tenant_archived", table_name="jobs")
    op.drop_index("ix_jobs_tenant_status", table_name="jobs")
    op.drop_index("ix_jobs_tenant_id", table_name="jobs")
    op.drop_table("jobs")
