"""Add nearby_schools JSON column to properties, replacing single nearest fields.

Revision ID: 031
Revises: 030
"""
from alembic import op
import sqlalchemy as sa

revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    # JSON column: [{name, phase, distance_mi, postcode, is_selective, ...}, ...]
    op.add_column('properties', sa.Column('nearby_schools', sa.Text(), nullable=True))
    op.add_column('properties', sa.Column('nearby_transport', sa.Text(), nullable=True))
    op.add_column('properties', sa.Column('planning_flags', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('properties', 'nearby_schools')
    op.drop_column('properties', 'nearby_transport')
    op.drop_column('properties', 'planning_flags')
