"""Add scrape_detail_pages option to scraper_sources

Revision ID: 004
Revises: 003
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scraper_sources',
        sa.Column('scrape_detail_pages', sa.Boolean(), nullable=True, server_default='false'))


def downgrade():
    op.drop_column('scraper_sources', 'scrape_detail_pages')
