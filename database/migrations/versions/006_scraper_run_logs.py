"""Add scraper_run_logs table

Revision ID: 006
Revises: 005
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scraper_run_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('run_type', sa.String(20), nullable=False, server_default='scrape'),
        sa.Column('level', sa.String(10), nullable=False, server_default='info'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['scraper_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_scraper_run_logs'),
    )
    op.create_index('ix_scraper_run_logs_id', 'scraper_run_logs', ['id'])
    op.create_index('ix_run_log_source_run', 'scraper_run_logs', ['source_id', 'run_id'])
    op.create_index('ix_run_log_created', 'scraper_run_logs', ['created_at'])


def downgrade():
    op.drop_table('scraper_run_logs')
