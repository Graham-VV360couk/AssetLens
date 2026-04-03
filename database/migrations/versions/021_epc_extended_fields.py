"""Add extended EPC Tier 1 fields to epc_certificates.

Revision ID: 021
Revises: 020
"""
from alembic import op
import sqlalchemy as sa

revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('epc_certificates', sa.Column('construction_age_band', sa.String(50), nullable=True))
    op.add_column('epc_certificates', sa.Column('current_energy_efficiency', sa.Integer(), nullable=True))
    op.add_column('epc_certificates', sa.Column('potential_energy_efficiency', sa.Integer(), nullable=True))
    op.add_column('epc_certificates', sa.Column('tenure', sa.String(50), nullable=True))
    op.add_column('epc_certificates', sa.Column('mains_gas_flag', sa.String(1), nullable=True))
    op.add_column('epc_certificates', sa.Column('heating_cost_current', sa.Float(), nullable=True))
    op.add_column('epc_certificates', sa.Column('heating_cost_potential', sa.Float(), nullable=True))
    op.add_column('epc_certificates', sa.Column('hot_water_cost_current', sa.Float(), nullable=True))
    op.add_column('epc_certificates', sa.Column('hot_water_cost_potential', sa.Float(), nullable=True))
    op.add_column('epc_certificates', sa.Column('lighting_cost_current', sa.Float(), nullable=True))
    op.add_column('epc_certificates', sa.Column('lighting_cost_potential', sa.Float(), nullable=True))
    op.add_column('epc_certificates', sa.Column('co2_emissions_current', sa.Float(), nullable=True))
    op.add_column('epc_certificates', sa.Column('number_habitable_rooms', sa.Integer(), nullable=True))
    op.add_column('epc_certificates', sa.Column('transaction_type', sa.String(50), nullable=True))
    op.add_column('epc_certificates', sa.Column('epc_expiry_date', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('epc_certificates', 'epc_expiry_date')
    op.drop_column('epc_certificates', 'transaction_type')
    op.drop_column('epc_certificates', 'number_habitable_rooms')
    op.drop_column('epc_certificates', 'co2_emissions_current')
    op.drop_column('epc_certificates', 'lighting_cost_potential')
    op.drop_column('epc_certificates', 'lighting_cost_current')
    op.drop_column('epc_certificates', 'hot_water_cost_potential')
    op.drop_column('epc_certificates', 'hot_water_cost_current')
    op.drop_column('epc_certificates', 'heating_cost_potential')
    op.drop_column('epc_certificates', 'heating_cost_current')
    op.drop_column('epc_certificates', 'mains_gas_flag')
    op.drop_column('epc_certificates', 'tenure')
    op.drop_column('epc_certificates', 'potential_energy_efficiency')
    op.drop_column('epc_certificates', 'current_energy_efficiency')
    op.drop_column('epc_certificates', 'construction_age_band')
