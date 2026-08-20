"""Enable RLS and create isolation policies for all tenant-scoped tables.

Revision ID: phase16_rls_001
Revises: b3b6a3f2c986
Create Date: 2026-08-11 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "phase16_rls_001"
down_revision: str | None = "b3b6a3f2c986"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_SCOPED_TABLES = [
    "users",
    "refresh_tokens",
    "jobs",
    "pipeline_stages",
    "candidates",
    "job_candidates",
    "resumes",
    "resume_files",
    "candidate_embeddings",
    "job_embeddings",
    "scores",
    "saved_searches",
    "candidate_stage_history",
    "candidate_notes",
    "candidate_tags",
    "audit_logs",
    "ai_usage_logs",
]


def upgrade() -> None:
    """Apply Row-Level Security policies to all tenant-scoped tables."""
    for table in TENANT_SCOPED_TABLES:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # Force RLS for table owners
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Create policies
        # 1. SELECT policy
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_select_policy ON {table}
            FOR SELECT
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)
            """
        )

        # 2. INSERT policy
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_insert_policy ON {table}
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::UUID)
            """
        )

        # 3. UPDATE policy
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_update_policy ON {table}
            FOR UPDATE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::UUID)
            """
        )

        # 4. DELETE policy
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_delete_policy ON {table}
            FOR DELETE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)
            """
        )


def downgrade() -> None:
    """Remove Row-Level Security policies from all tenant-scoped tables."""
    for table in reversed(TENANT_SCOPED_TABLES):
        # Drop policies
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_select_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_insert_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_update_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_delete_policy ON {table}")

        # Disable RLS
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
