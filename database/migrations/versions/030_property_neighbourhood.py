"""Add neighbourhood enrichment columns to properties.

Stores pre-computed neighbourhood data so property detail loads are fast.

Revision ID: 030
Revises: 029
"""
from alembic import op
import sqlalchemy as sa

revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade():
    # Postcode-derived fields
    op.add_column('properties', sa.Column('lsoa_code', sa.String(15), nullable=True))
    op.add_column('properties', sa.Column('msoa_code', sa.String(15), nullable=True))
    op.add_column('properties', sa.Column('lad_code', sa.String(9), nullable=True))
    op.add_column('properties', sa.Column('imd_rank', sa.Integer(), nullable=True))
    op.add_column('properties', sa.Column('rural_urban', sa.String(2), nullable=True))

    # Broadband
    op.add_column('properties', sa.Column('broadband_gigabit_pct', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('broadband_sfbb_pct', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('broadband_below_uso_pct', sa.Float(), nullable=True))

    # Crime
    op.add_column('properties', sa.Column('crime_count_1yr', sa.Integer(), nullable=True))
    op.add_column('properties', sa.Column('crime_rate_band', sa.String(20), nullable=True))
    op.add_column('properties', sa.Column('crime_trend', sa.String(20), nullable=True))

    # Nearest school
    op.add_column('properties', sa.Column('nearest_primary_name', sa.String(200), nullable=True))
    op.add_column('properties', sa.Column('nearest_primary_distance_mi', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('nearest_secondary_name', sa.String(200), nullable=True))
    op.add_column('properties', sa.Column('nearest_secondary_distance_mi', sa.Float(), nullable=True))

    # Nearest transport
    op.add_column('properties', sa.Column('nearest_station_name', sa.String(200), nullable=True))
    op.add_column('properties', sa.Column('nearest_station_distance_mi', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('nearest_station_type', sa.String(10), nullable=True))
    op.add_column('properties', sa.Column('nearest_bus_name', sa.String(200), nullable=True))
    op.add_column('properties', sa.Column('nearest_bus_distance_mi', sa.Float(), nullable=True))

    # Planning constraints (boolean flags for key ones)
    op.add_column('properties', sa.Column('in_conservation_area', sa.Boolean(), nullable=True))
    op.add_column('properties', sa.Column('in_flood_zone', sa.String(10), nullable=True))
    op.add_column('properties', sa.Column('in_green_belt', sa.Boolean(), nullable=True))
    op.add_column('properties', sa.Column('has_article4', sa.Boolean(), nullable=True))
    op.add_column('properties', sa.Column('is_listed_building', sa.String(5), nullable=True))

    # Enrichment tracking
    op.add_column('properties', sa.Column('neighbourhood_enriched_at', sa.DateTime(), nullable=True))

    op.create_index('ix_property_lsoa', 'properties', ['lsoa_code'])
    op.create_index('ix_property_imd', 'properties', ['imd_rank'])


def downgrade():
    op.drop_index('ix_property_imd', 'properties')
    op.drop_index('ix_property_lsoa', 'properties')

    for col in [
        'lsoa_code', 'msoa_code', 'lad_code', 'imd_rank', 'rural_urban',
        'broadband_gigabit_pct', 'broadband_sfbb_pct', 'broadband_below_uso_pct',
        'crime_count_1yr', 'crime_rate_band', 'crime_trend',
        'nearest_primary_name', 'nearest_primary_distance_mi',
        'nearest_secondary_name', 'nearest_secondary_distance_mi',
        'nearest_station_name', 'nearest_station_distance_mi', 'nearest_station_type',
        'nearest_bus_name', 'nearest_bus_distance_mi',
        'in_conservation_area', 'in_flood_zone', 'in_green_belt',
        'has_article4', 'is_listed_building',
        'neighbourhood_enriched_at',
    ]:
        op.drop_column('properties', col)
