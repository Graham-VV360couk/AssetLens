"""Add scraper_strategy_library table

Revision ID: 005
Revises: 004
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scraper_strategy_library',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('probe_id', sa.String(100), nullable=False),
        sa.Column('domain', sa.String(200), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fail_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_success_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_scraper_strategy_library'),
    )
    op.create_index('ix_scraper_strategy_library_id', 'scraper_strategy_library', ['id'])
    op.create_index('ix_library_probe_domain', 'scraper_strategy_library', ['probe_id', 'domain'], unique=True)
    op.create_index('ix_library_success', 'scraper_strategy_library', ['success_count'])


def downgrade():
    op.drop_table('scraper_strategy_library')
