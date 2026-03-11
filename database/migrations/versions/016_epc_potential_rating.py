"""Add potential_energy_rating column to epc_certificates

Revision ID: 016
Revises: 015
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'epc_certificates',
        sa.Column('potential_energy_rating', sa.String(5), nullable=True),
    )


def downgrade():
    op.drop_column('epc_certificates', 'potential_energy_rating')
