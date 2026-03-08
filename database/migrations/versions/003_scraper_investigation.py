"""Add investigation columns to scraper_sources

Revision ID: 003
Revises: 002
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scraper_sources', sa.Column('investigation_status', sa.String(20), nullable=True))
    op.add_column('scraper_sources', sa.Column('investigation_ran_at', sa.DateTime(), nullable=True))
    op.add_column('scraper_sources', sa.Column('investigation_data', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('scraper_sources', 'investigation_data')
    op.drop_column('scraper_sources', 'investigation_ran_at')
    op.drop_column('scraper_sources', 'investigation_status')
