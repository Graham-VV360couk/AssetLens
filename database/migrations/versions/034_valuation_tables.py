"""Create user_properties and property_valuations tables.

Revision ID: 034
Revises: 033
"""
from alembic import op
import sqlalchemy as sa

revision = '034'
down_revision = '033'
branch_labels = None
depends_on = None


def upgrade():
    # User's property portfolio — properties they own/manage
    op.create_table(
        'user_properties',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('address_line1', sa.String(200), nullable=False),
        sa.Column('address_line2', sa.String(200), nullable=True),
        sa.Column('town', sa.String(100), nullable=False),
        sa.Column('postcode', sa.String(10), nullable=False, index=True),
        sa.Column('property_type', sa.String(30), nullable=False),
        sa.Column('bedrooms', sa.Integer(), nullable=False),
        sa.Column('bathrooms', sa.Integer(), nullable=True),
        sa.Column('relationship_to_property', sa.String(30), nullable=False),
        sa.Column('tenure', sa.String(20), nullable=False),
        sa.Column('lease_years_remaining', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Versioned valuation results — never overwrite, always append
    op.create_table(
        'property_valuations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_property_id', sa.Integer(), sa.ForeignKey('user_properties.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),

        # All question answers stored as JSON (versioned, never overwrite)
        sa.Column('answers_json', sa.Text(), nullable=False),

        # AVM baseline
        sa.Column('avm_baseline', sa.Float(), nullable=True),
        sa.Column('avm_source', sa.String(50), nullable=True),

        # Adjustments
        sa.Column('feature_adjustment', sa.Float(), nullable=True),
        sa.Column('condition_adjustment', sa.Float(), nullable=True),
        sa.Column('situation_band', sa.String(20), nullable=True),
        sa.Column('situation_band_pct', sa.Float(), nullable=True),

        # Output range
        sa.Column('range_low', sa.Float(), nullable=True),
        sa.Column('range_mid', sa.Float(), nullable=True),
        sa.Column('range_high', sa.Float(), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('property_valuations')
    op.drop_table('user_properties')
