"""Create postcodes table for ONS Postcode Directory (ONSPD).

Revision ID: 026
Revises: 025
"""
from alembic import op
import sqlalchemy as sa

revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'postcodes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('postcode', sa.String(8), unique=True, nullable=False, index=True),
        sa.Column('date_introduced', sa.String(6), nullable=True),
        sa.Column('date_terminated', sa.String(6), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('easting', sa.Integer(), nullable=True),
        sa.Column('northing', sa.Integer(), nullable=True),
        sa.Column('grid_quality', sa.SmallInteger(), nullable=True),
        sa.Column('lad_code', sa.String(9), nullable=True, index=True),
        sa.Column('ward_code', sa.String(9), nullable=True),
        sa.Column('county_code', sa.String(9), nullable=True),
        sa.Column('region_code', sa.String(9), nullable=True, index=True),
        sa.Column('country_code', sa.String(9), nullable=True),
        sa.Column('pcon_code', sa.String(9), nullable=True),
        sa.Column('parish_code', sa.String(9), nullable=True),
        sa.Column('oa21_code', sa.String(9), nullable=True),
        sa.Column('lsoa11_code', sa.String(9), nullable=True, index=True),
        sa.Column('lsoa21_code', sa.String(9), nullable=True, index=True),
        sa.Column('msoa11_code', sa.String(9), nullable=True),
        sa.Column('msoa21_code', sa.String(9), nullable=True),
        sa.Column('imd_rank', sa.Integer(), nullable=True, index=True),
        sa.Column('rural_urban', sa.String(2), nullable=True),
        sa.Column('oac11', sa.String(3), nullable=True),
        sa.Column('pfa_code', sa.String(9), nullable=True, index=True),
        sa.Column('icb_code', sa.String(9), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_postcode_lat_lng', 'postcodes', ['latitude', 'longitude'])


def downgrade():
    op.drop_table('postcodes')
