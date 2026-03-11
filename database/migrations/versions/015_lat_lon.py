"""Add latitude and longitude columns to properties table

Revision ID: 015
Revises: 014
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('properties', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('longitude', sa.Float(), nullable=True))
    op.create_index('ix_properties_latitude', 'properties', ['latitude'])
    op.create_index('ix_properties_longitude', 'properties', ['longitude'])


def downgrade():
    op.drop_index('ix_properties_longitude', table_name='properties')
    op.drop_index('ix_properties_latitude', table_name='properties')
    op.drop_column('properties', 'longitude')
    op.drop_column('properties', 'latitude')
