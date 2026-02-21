"""add key_prefix to api_keys

Revision ID: 004_api_key_prefix
Revises: 003_audit_logs
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_api_key_prefix'
down_revision = '003_audit_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'api_keys',
        sa.Column('key_prefix', sa.String(20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('api_keys', 'key_prefix')
