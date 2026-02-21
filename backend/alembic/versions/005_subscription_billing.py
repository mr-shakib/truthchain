"""add subscription billing fields to organizations

Revision ID: 005_subscription_billing
Revises: 004_api_key_prefix
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_subscription_billing'
down_revision = '004_api_key_prefix'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stripe references
    op.add_column('organizations', sa.Column('stripe_customer_id', sa.String(64), nullable=True))
    op.add_column('organizations', sa.Column('stripe_subscription_id', sa.String(64), nullable=True))

    # Billing contact email (may differ from login email)
    op.add_column('organizations', sa.Column('billing_email', sa.String(255), nullable=True))

    # Subscription lifecycle
    op.add_column(
        'organizations',
        sa.Column('subscription_status', sa.String(20), nullable=False, server_default='active')
    )
    op.add_column('organizations', sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organizations', sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organizations', sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True))

    # Invoice history (JSON array stored in Postgres)
    op.add_column('organizations', sa.Column('invoices_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('organizations', 'invoices_json')
    op.drop_column('organizations', 'trial_ends_at')
    op.drop_column('organizations', 'canceled_at')
    op.drop_column('organizations', 'current_period_end')
    op.drop_column('organizations', 'subscription_status')
    op.drop_column('organizations', 'billing_email')
    op.drop_column('organizations', 'stripe_subscription_id')
    op.drop_column('organizations', 'stripe_customer_id')
