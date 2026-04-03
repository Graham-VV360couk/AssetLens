"""Create planning_designations table for planning.data.gov.uk data.

Revision ID: 027
Revises: 026
"""
from alembic import op
import sqlalchemy as sa

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'planning_designations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('dataset', sa.String(60), nullable=False, index=True),
        sa.Column('entity', sa.Integer(), nullable=False, index=True),
        sa.Column('name', sa.String(500), nullable=True),
        sa.Column('reference', sa.String(200), nullable=True, index=True),
        sa.Column('organisation', sa.String(200), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('entry_date', sa.Date(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('listed_building_grade', sa.String(5), nullable=True),
        sa.Column('flood_risk_level', sa.String(10), nullable=True),
        sa.Column('flood_risk_type', sa.String(50), nullable=True),
        sa.Column('permitted_dev_rights', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hectares', sa.Float(), nullable=True),
        sa.Column('max_net_dwellings', sa.Integer(), nullable=True),
        sa.Column('min_net_dwellings', sa.Integer(), nullable=True),
        sa.Column('designation_date', sa.Date(), nullable=True),
        sa.Column('ancient_woodland_status', sa.String(100), nullable=True),
        sa.Column('heritage_at_risk', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_planning_dataset_entity', 'planning_designations', ['dataset', 'entity'], unique=True)
    op.create_index('ix_planning_lat_lng', 'planning_designations', ['latitude', 'longitude'])


def downgrade():
    op.drop_table('planning_designations')
