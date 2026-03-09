"""Add PropertyData enrichment columns to property_scores

Revision ID: 008
Revises: 007
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('property_scores', sa.Column('pd_avm', sa.Float(), nullable=True))
    op.add_column('property_scores', sa.Column('pd_avm_lower', sa.Float(), nullable=True))
    op.add_column('property_scores', sa.Column('pd_avm_upper', sa.Float(), nullable=True))
    op.add_column('property_scores', sa.Column('pd_rental_estimate', sa.Float(), nullable=True))
    op.add_column('property_scores', sa.Column('pd_flood_risk', sa.String(20), nullable=True))
    op.add_column('property_scores', sa.Column('pd_enriched_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('property_scores', 'pd_enriched_at')
    op.drop_column('property_scores', 'pd_flood_risk')
    op.drop_column('property_scores', 'pd_rental_estimate')
    op.drop_column('property_scores', 'pd_avm_upper')
    op.drop_column('property_scores', 'pd_avm_lower')
    op.drop_column('property_scores', 'pd_avm')
