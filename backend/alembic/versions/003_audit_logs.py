"""add audit logs table

Revision ID: 003_audit_logs
Revises: e89d6a10bbb6
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_audit_logs'
down_revision = 'e89d6a10bbb6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_category', sa.String(50), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_email', sa.String(255), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('event_metadata', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Create indexes for common queries
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_category', 'audit_logs', ['event_category'])
    op.create_index('idx_audit_org_id', 'audit_logs', ['organization_id'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_org_created', 'audit_logs', ['organization_id', 'created_at'])
    op.create_index('idx_audit_event_created', 'audit_logs', ['event_type', 'created_at'])
    op.create_index('idx_audit_category_created', 'audit_logs', ['event_category', 'created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_audit_category_created', 'audit_logs')
    op.drop_index('idx_audit_event_created', 'audit_logs')
    op.drop_index('idx_audit_org_created', 'audit_logs')
    op.drop_index('idx_audit_created', 'audit_logs')
    op.drop_index('idx_audit_org_id', 'audit_logs')
    op.drop_index('idx_audit_category', 'audit_logs')
    op.drop_index('idx_audit_event_type', 'audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')
