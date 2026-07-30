"""create_resumes_and_resume_files_tables

Revision ID: 000000000006
Revises: 000000000005
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000006"
down_revision: str | None = "000000000005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create resumes and resume_files tables with constraints and indexes per Database Design §5.6 & §5.7."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Create resumes table
    op.create_table(
        "resumes",
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
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "parsed_data",
            postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "parse_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "parser_model_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "parse_confidence",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "raw_text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "raw_text_hash",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "is_primary",
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
            name="fk_resumes_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="fk_resumes_candidate",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'parsed', 'failed')",
            name="ck_resumes_status",
        ),
        sa.CheckConstraint(
            "parse_confidence IS NULL OR (parse_confidence >= 0.0 AND parse_confidence <= 1.0)",
            name="ck_resumes_confidence_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resumes"),
    )

    # Partial unique index for primary resume per candidate
    op.create_index(
        "uq_resumes_candidate_primary",
        "resumes",
        ["candidate_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = TRUE"),
        sqlite_where=sa.text("is_primary = TRUE"),
    )

    # Standard resume indexes
    op.create_index("ix_resumes_tenant_id", "resumes", ["tenant_id"])
    op.create_index("ix_resumes_candidate_id", "resumes", ["candidate_id"])
    op.create_index("ix_resumes_tenant_status", "resumes", ["tenant_id", "status"])
    op.create_index("ix_resumes_raw_text_hash", "resumes", ["tenant_id", "raw_text_hash"])

    # 2. Create resume_files table
    op.create_table(
        "resume_files",
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
            "resume_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "s3_bucket",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "s3_key",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "file_size_bytes",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "checksum_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_resume_files_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name="fk_resume_files_resume",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "content_type IN ('application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain')",
            name="ck_resume_files_content_type",
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0 AND file_size_bytes <= 10485760",
            name="ck_resume_files_size",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_files"),
    )

    op.create_index("ix_resume_files_resume_id", "resume_files", ["resume_id"])
    op.create_index("ix_resume_files_tenant_id", "resume_files", ["tenant_id"])


def downgrade() -> None:
    """Drop resumes and resume_files tables and indexes."""
    op.drop_index("ix_resume_files_tenant_id", table_name="resume_files")
    op.drop_index("ix_resume_files_resume_id", table_name="resume_files")
    op.drop_table("resume_files")

    op.drop_index("ix_resumes_raw_text_hash", table_name="resumes")
    op.drop_index("ix_resumes_tenant_status", table_name="resumes")
    op.drop_index("ix_resumes_candidate_id", table_name="resumes")
    op.drop_index("ix_resumes_tenant_id", table_name="resumes")
    op.drop_index("uq_resumes_candidate_primary", table_name="resumes")
    op.drop_table("resumes")
