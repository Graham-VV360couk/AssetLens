"""Add EPC compliance columns to properties table

Revision ID: 018
Revises: 017
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('properties', sa.Column('epc_potential_rating', sa.String(5), nullable=True))
    op.add_column('properties', sa.Column('epc_compliance_cost_low', sa.Integer(), nullable=True))
    op.add_column('properties', sa.Column('epc_compliance_cost_high', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('properties', 'epc_compliance_cost_high')
    op.drop_column('properties', 'epc_compliance_cost_low')
    op.drop_column('properties', 'epc_potential_rating')
