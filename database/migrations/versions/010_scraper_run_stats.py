"""Add last_run_new and last_run_merged columns to scraper_sources

Revision ID: 010
Revises: 009
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scraper_sources', sa.Column('last_run_new', sa.Integer(), nullable=True))
    op.add_column('scraper_sources', sa.Column('last_run_merged', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('scraper_sources', 'last_run_merged')
    op.drop_column('scraper_sources', 'last_run_new')
