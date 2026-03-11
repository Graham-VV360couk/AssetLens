"""Create epc_certificates table

Revision ID: 013
Revises: 012
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'epc_certificates',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('lmk_key', sa.String(100), nullable=True),
        sa.Column('address1', sa.String(200), nullable=True),
        sa.Column('address2', sa.String(200), nullable=True),
        sa.Column('postcode', sa.String(10), nullable=True),
        sa.Column('uprn', sa.String(20), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=True),
        sa.Column('built_form', sa.String(50), nullable=True),
        sa.Column('floor_area_sqm', sa.Float(), nullable=True),
        sa.Column('energy_rating', sa.String(5), nullable=True),
        sa.Column('inspection_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_epc_lmk_key', 'epc_certificates', ['lmk_key'], unique=True)
    op.create_index('ix_epc_postcode', 'epc_certificates', ['postcode'])
    op.create_index('ix_epc_uprn', 'epc_certificates', ['uprn'])


def downgrade():
    op.drop_index('ix_epc_uprn', table_name='epc_certificates')
    op.drop_index('ix_epc_postcode', table_name='epc_certificates')
    op.drop_index('ix_epc_lmk_key', table_name='epc_certificates')
    op.drop_table('epc_certificates')
