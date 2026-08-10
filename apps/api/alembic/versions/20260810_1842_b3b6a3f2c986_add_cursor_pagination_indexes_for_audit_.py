"""Add cursor pagination indexes for audit and ai usage

Revision ID: b3b6a3f2c986
Revises: '000000000015'
Create Date: 2026-08-10 18:42:12.437370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3b6a3f2c986'
down_revision: Union[str, None] = '000000000015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_audit_logs_cursor_pagination', 'audit_logs', [sa.text('tenant_id'), sa.text('created_at DESC'), sa.text('id DESC')])
    op.create_index('ix_ai_usage_logs_cursor_pagination', 'ai_usage_logs', [sa.text('tenant_id'), sa.text('created_at DESC'), sa.text('id DESC')])


def downgrade() -> None:
    op.drop_index('ix_ai_usage_logs_cursor_pagination', table_name='ai_usage_logs')
    op.drop_index('ix_audit_logs_cursor_pagination', table_name='audit_logs')
