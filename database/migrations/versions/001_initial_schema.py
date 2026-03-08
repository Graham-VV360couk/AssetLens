"""Initial AssetLens database schema

Revision ID: 001_initial
Revises:
Create Date: 2026-02-02

Creates all core tables for nationwide UK property investment intelligence:
- Properties: Core property records
- PropertySources: Multi-source tracking for deduplication
- PropertyScores: Investment scoring and valuation
- SalesHistory: Land Registry 10-year historical data
- Rentals: Rental listings for yield calculations
- HMORegisters: HMO licensing data
- Auctions: Auction property listings
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create properties table
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('postcode', sa.String(10), nullable=False),
        sa.Column('town', sa.String(100), nullable=True),
        sa.Column('county', sa.String(100), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=False),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('bathrooms', sa.Integer(), nullable=True),
        sa.Column('reception_rooms', sa.Integer(), nullable=True),
        sa.Column('floor_area_sqm', sa.Float(), nullable=True),
        sa.Column('plot_size_sqm', sa.Float(), nullable=True),
        sa.Column('asking_price', sa.Float(), nullable=True),
        sa.Column('price_qualifier', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('date_found', sa.Date(), nullable=False),
        sa.Column('date_sold', sa.Date(), nullable=True),
        sa.Column('is_reviewed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id', name='pk_properties')
    )

    # Property indexes
    op.create_index('ix_properties_id', 'properties', ['id'])
    op.create_index('ix_properties_postcode', 'properties', ['postcode'])
    op.create_index('ix_properties_status', 'properties', ['status'])
    op.create_index('ix_properties_date_found', 'properties', ['date_found'])
    op.create_index('ix_property_postcode_type_status', 'properties', ['postcode', 'property_type', 'status'])
    op.create_index('ix_property_status_date_found', 'properties', ['status', 'date_found'])
    op.create_index('ix_property_reviewed', 'properties', ['is_reviewed', 'reviewed_at'])

    # Create property_sources table
    op.create_table(
        'property_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name='fk_property_sources_property_id_properties'),
        sa.PrimaryKeyConstraint('id', name='pk_property_sources')
    )

    op.create_index('ix_property_sources_id', 'property_sources', ['id'])
    op.create_index('ix_property_sources_property_id', 'property_sources', ['property_id'])
    op.create_index('ix_source_name_id', 'property_sources', ['source_name', 'source_id'])
    op.create_index('ix_source_active', 'property_sources', ['is_active', 'last_seen_at'])

    # Create sales_history table
    op.create_table(
        'sales_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('sale_date', sa.Date(), nullable=False),
        sa.Column('sale_price', sa.Float(), nullable=False),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('postcode', sa.String(10), nullable=False),
        sa.Column('town', sa.String(100), nullable=True),
        sa.Column('county', sa.String(100), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=False),
        sa.Column('old_new', sa.String(1), nullable=True),
        sa.Column('duration', sa.String(1), nullable=True),
        sa.Column('ppd_category_type', sa.String(1), nullable=True),
        sa.Column('record_status', sa.String(1), nullable=True),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name='fk_sales_history_property_id_properties'),
        sa.PrimaryKeyConstraint('id', name='pk_sales_history')
    )

    op.create_index('ix_sales_history_id', 'sales_history', ['id'])
    op.create_index('ix_sales_history_property_id', 'sales_history', ['property_id'])
    op.create_index('ix_sales_history_sale_date', 'sales_history', ['sale_date'])
    op.create_index('ix_sales_history_postcode', 'sales_history', ['postcode'])
    op.create_index('ix_sales_history_transaction_id', 'sales_history', ['transaction_id'], unique=True)
    op.create_index('ix_sales_postcode_date', 'sales_history', ['postcode', 'sale_date'])
    op.create_index('ix_sales_postcode_type', 'sales_history', ['postcode', 'property_type'])
    op.create_index('ix_sales_date_price', 'sales_history', ['sale_date', 'sale_price'])

    # Create rentals table
    op.create_table(
        'rentals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('rent_monthly', sa.Float(), nullable=False),
        sa.Column('rent_per_room', sa.Float(), nullable=True),
        sa.Column('postcode', sa.String(10), nullable=False),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=True),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('num_rooms', sa.Integer(), nullable=True),
        sa.Column('date_listed', sa.Date(), nullable=False),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('is_hmo', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_aggregated', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name='fk_rentals_property_id_properties'),
        sa.PrimaryKeyConstraint('id', name='pk_rentals')
    )

    op.create_index('ix_rentals_id', 'rentals', ['id'])
    op.create_index('ix_rentals_property_id', 'rentals', ['property_id'])
    op.create_index('ix_rentals_postcode', 'rentals', ['postcode'])
    op.create_index('ix_rentals_date_listed', 'rentals', ['date_listed'])
    op.create_index('ix_rental_postcode_date', 'rentals', ['postcode', 'date_listed'])
    op.create_index('ix_rental_postcode_type', 'rentals', ['postcode', 'property_type'])
    op.create_index('ix_rental_aggregated', 'rentals', ['is_aggregated', 'postcode'])

    # Create hmo_registers table
    op.create_table(
        'hmo_registers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('licence_number', sa.String(100), nullable=True),
        sa.Column('licence_start', sa.Date(), nullable=False),
        sa.Column('licence_expiry', sa.Date(), nullable=False),
        sa.Column('licence_status', sa.String(20), nullable=True),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('postcode', sa.String(10), nullable=False),
        sa.Column('num_rooms', sa.Integer(), nullable=True),
        sa.Column('max_occupants', sa.Integer(), nullable=True),
        sa.Column('num_households', sa.Integer(), nullable=True),
        sa.Column('council', sa.String(100), nullable=False),
        sa.Column('council_reference', sa.String(100), nullable=True),
        sa.Column('licence_holder_name', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name='fk_hmo_registers_property_id_properties'),
        sa.PrimaryKeyConstraint('id', name='pk_hmo_registers')
    )

    op.create_index('ix_hmo_registers_id', 'hmo_registers', ['id'])
    op.create_index('ix_hmo_registers_property_id', 'hmo_registers', ['property_id'])
    op.create_index('ix_hmo_registers_postcode', 'hmo_registers', ['postcode'])
    op.create_index('ix_hmo_registers_licence_expiry', 'hmo_registers', ['licence_expiry'])
    op.create_index('ix_hmo_registers_council', 'hmo_registers', ['council'])
    op.create_index('ix_hmo_registers_licence_number', 'hmo_registers', ['licence_number'], unique=True)
    op.create_index('ix_hmo_postcode_status', 'hmo_registers', ['postcode', 'licence_status'])
    op.create_index('ix_hmo_council_status', 'hmo_registers', ['council', 'licence_status'])
    op.create_index('ix_hmo_expiry', 'hmo_registers', ['licence_expiry'])

    # Create auctions table
    op.create_table(
        'auctions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('auction_date', sa.DateTime(), nullable=False),
        sa.Column('auctioneer', sa.String(100), nullable=False),
        sa.Column('auction_house_url', sa.String(500), nullable=True),
        sa.Column('lot_number', sa.String(50), nullable=True),
        sa.Column('guide_price', sa.Float(), nullable=True),
        sa.Column('reserve_price', sa.Float(), nullable=True),
        sa.Column('sold_price', sa.Float(), nullable=True),
        sa.Column('is_sold', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('sale_status', sa.String(50), nullable=True),
        sa.Column('legal_pack_url', sa.String(1000), nullable=True),
        sa.Column('legal_pack_downloaded', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tenure', sa.String(50), nullable=True),
        sa.Column('viewing_date', sa.DateTime(), nullable=True),
        sa.Column('auction_reference', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name='fk_auctions_property_id_properties'),
        sa.PrimaryKeyConstraint('id', name='pk_auctions')
    )

    op.create_index('ix_auctions_id', 'auctions', ['id'])
    op.create_index('ix_auctions_property_id', 'auctions', ['property_id'])
    op.create_index('ix_auctions_auction_date', 'auctions', ['auction_date'])
    op.create_index('ix_auctions_auction_reference', 'auctions', ['auction_reference'], unique=True)
    op.create_index('ix_auction_date_status', 'auctions', ['auction_date', 'is_sold'])
    op.create_index('ix_auction_auctioneer', 'auctions', ['auctioneer', 'auction_date'])

    # Create property_scores table
    op.create_table(
        'property_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('estimated_value', sa.Float(), nullable=True),
        sa.Column('valuation_confidence', sa.Float(), nullable=True),
        sa.Column('price_deviation_pct', sa.Float(), nullable=True),
        sa.Column('price_score', sa.Float(), nullable=True),
        sa.Column('estimated_monthly_rent', sa.Float(), nullable=True),
        sa.Column('gross_yield_pct', sa.Float(), nullable=True),
        sa.Column('yield_score', sa.Float(), nullable=True),
        sa.Column('area_trend_score', sa.Float(), nullable=True),
        sa.Column('area_avg_price', sa.Float(), nullable=True),
        sa.Column('area_growth_10yr_pct', sa.Float(), nullable=True),
        sa.Column('investment_score', sa.Float(), nullable=True),
        sa.Column('price_band', sa.String(20), nullable=True),
        sa.Column('hmo_opportunity_score', sa.Float(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('model_version', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name='fk_property_scores_property_id_properties'),
        sa.PrimaryKeyConstraint('id', name='pk_property_scores')
    )

    op.create_index('ix_property_scores_id', 'property_scores', ['id'])
    op.create_index('ix_property_scores_property_id', 'property_scores', ['property_id'], unique=True)
    op.create_index('ix_score_investment', 'property_scores', ['investment_score'])
    op.create_index('ix_score_yield', 'property_scores', ['yield_score'])
    op.create_index('ix_score_price_band', 'property_scores', ['price_band'])
    op.create_index('ix_score_calculated_at', 'property_scores', ['calculated_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('property_scores')
    op.drop_table('auctions')
    op.drop_table('hmo_registers')
    op.drop_table('rentals')
    op.drop_table('sales_history')
    op.drop_table('property_sources')
    op.drop_table('properties')
