"""Create user_alert_preferences table.

Revision ID: 033
Revises: 032
"""
from alembic import op
import sqlalchemy as sa

revision = '033'
down_revision = '032'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_alert_preferences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('min_match_pct', sa.Integer(), server_default='60', nullable=False),
        sa.Column('alert_frequency', sa.String(20), server_default='daily', nullable=False),  # immediate, daily, weekly
        sa.Column('location_filter', sa.String(200), nullable=True),  # comma-separated postcodes/districts
        sa.Column('max_price', sa.Integer(), nullable=True),
        sa.Column('min_beds', sa.Integer(), nullable=True),
        sa.Column('property_types', sa.String(200), nullable=True),  # comma-separated types
        sa.Column('last_alerted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('user_alert_preferences')
