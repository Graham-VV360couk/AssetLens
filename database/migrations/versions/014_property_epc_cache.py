"""Add EPC cache columns to properties table

Revision ID: 014
Revises: 013
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('properties', sa.Column('epc_floor_area_sqm', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('epc_property_type', sa.String(50), nullable=True))
    op.add_column('properties', sa.Column('epc_energy_rating', sa.String(5), nullable=True))
    op.add_column('properties', sa.Column('epc_inspection_date', sa.Date(), nullable=True))
    op.add_column('properties', sa.Column('epc_matched_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('properties', 'epc_matched_at')
    op.drop_column('properties', 'epc_inspection_date')
    op.drop_column('properties', 'epc_energy_rating')
    op.drop_column('properties', 'epc_property_type')
    op.drop_column('properties', 'epc_floor_area_sqm')
