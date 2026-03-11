"""Create epc_recommendations table

Revision ID: 017
Revises: 016
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'epc_recommendations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lmk_key', sa.String(100), nullable=False, index=True),
        sa.Column('improvement_item', sa.String(100), nullable=True),
        sa.Column('improvement_summary_text', sa.String(500), nullable=True),
        sa.Column('improvement_descr_text', sa.Text(), nullable=True),
        sa.Column('indicative_cost_raw', sa.String(100), nullable=True),
        sa.Column('indicative_cost_low', sa.Integer(), nullable=True),
        sa.Column('indicative_cost_high', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_epc_rec_lmk_key', 'epc_recommendations', ['lmk_key'])


def downgrade():
    op.drop_index('ix_epc_rec_lmk_key', table_name='epc_recommendations')
    op.drop_table('epc_recommendations')
