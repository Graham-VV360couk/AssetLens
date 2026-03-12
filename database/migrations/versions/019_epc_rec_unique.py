"""Add unique constraint on epc_recommendations (lmk_key, improvement_item) for idempotent re-runs

Revision ID: 019
Revises: 018
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the plain index (it will be replaced by the unique index)
    op.drop_index('ix_epc_rec_lmk_key', table_name='epc_recommendations', if_exists=True)
    # Add unique constraint — enables ON CONFLICT DO NOTHING on re-runs
    op.create_unique_constraint(
        'uq_epc_rec_lmk_key_item',
        'epc_recommendations',
        ['lmk_key', 'improvement_item'],
    )
    # Recreate a non-unique index on lmk_key alone for lookup performance
    op.create_index('ix_epc_rec_lmk_key', 'epc_recommendations', ['lmk_key'])


def downgrade():
    op.drop_index('ix_epc_rec_lmk_key', table_name='epc_recommendations')
    op.drop_constraint('uq_epc_rec_lmk_key_item', 'epc_recommendations', type_='unique')
    op.create_index('ix_epc_rec_lmk_key', 'epc_recommendations', ['lmk_key'])
