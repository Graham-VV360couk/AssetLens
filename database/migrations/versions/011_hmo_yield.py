"""Add hmo_gross_yield_pct column to property_scores

Revision ID: 011
Revises: 010
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('property_scores', sa.Column('hmo_gross_yield_pct', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('property_scores', 'hmo_gross_yield_pct')
