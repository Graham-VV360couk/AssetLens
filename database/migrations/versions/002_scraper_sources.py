"""Add scraper_sources table

Revision ID: 002
Revises: 001
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scraper_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=True, default='auction'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('max_pages', sa.Integer(), nullable=True, default=5),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_status', sa.String(20), nullable=True),
        sa.Column('last_run_properties', sa.Integer(), nullable=True, default=0),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('total_properties_found', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scraper_sources_id', 'scraper_sources', ['id'])


def downgrade():
    op.drop_index('ix_scraper_sources_id', 'scraper_sources')
    op.drop_table('scraper_sources')
