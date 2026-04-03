"""Create broadband_coverage table for Ofcom data.

Revision ID: 029
Revises: 028
"""
from alembic import op
import sqlalchemy as sa

revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'broadband_coverage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('postcode', sa.String(8), unique=True, nullable=False, index=True),
        sa.Column('sfbb_availability', sa.Float(), nullable=True),
        sa.Column('ufbb_100_availability', sa.Float(), nullable=True),
        sa.Column('ufbb_availability', sa.Float(), nullable=True),
        sa.Column('gigabit_availability', sa.Float(), nullable=True),
        sa.Column('pct_below_2', sa.Float(), nullable=True),
        sa.Column('pct_2_to_5', sa.Float(), nullable=True),
        sa.Column('pct_5_to_10', sa.Float(), nullable=True),
        sa.Column('pct_10_to_30', sa.Float(), nullable=True),
        sa.Column('pct_30_to_300', sa.Float(), nullable=True),
        sa.Column('pct_above_300', sa.Float(), nullable=True),
        sa.Column('pct_unable_2', sa.Float(), nullable=True),
        sa.Column('pct_unable_5', sa.Float(), nullable=True),
        sa.Column('pct_unable_10', sa.Float(), nullable=True),
        sa.Column('pct_unable_30', sa.Float(), nullable=True),
        sa.Column('pct_below_uso', sa.Float(), nullable=True),
        sa.Column('pct_nga', sa.Float(), nullable=True),
        sa.Column('pct_fwa_decent', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('broadband_coverage')
