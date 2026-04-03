"""Create crimes table for UK police street-level crime data.

Revision ID: 025
Revises: 024
"""
from alembic import op
import sqlalchemy as sa

revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'crimes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('crime_id', sa.String(70), nullable=True, index=True),
        sa.Column('month', sa.Date(), nullable=False, index=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('falls_within', sa.String(100), nullable=True),
        sa.Column('lsoa_code', sa.String(15), nullable=True, index=True),
        sa.Column('lsoa_name', sa.String(100), nullable=True),
        sa.Column('crime_type', sa.String(50), nullable=False, index=True),
        sa.Column('last_outcome', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_crime_lsoa_month', 'crimes', ['lsoa_code', 'month'])
    op.create_index('ix_crime_lat_lng', 'crimes', ['latitude', 'longitude'])
    op.create_index('ix_crime_type_month', 'crimes', ['crime_type', 'month'])


def downgrade():
    op.drop_table('crimes')
