"""Add extended fields to epc_recommendations.

Revision ID: 022
Revises: 021
"""
from alembic import op
import sqlalchemy as sa

revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('epc_recommendations', sa.Column('typical_saving', sa.Float(), nullable=True))
    op.add_column('epc_recommendations', sa.Column('efficiency_rating_before', sa.Integer(), nullable=True))
    op.add_column('epc_recommendations', sa.Column('efficiency_rating_after', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('epc_recommendations', 'efficiency_rating_after')
    op.drop_column('epc_recommendations', 'efficiency_rating_before')
    op.drop_column('epc_recommendations', 'typical_saving')
