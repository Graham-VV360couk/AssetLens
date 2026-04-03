"""Create transport_stops table for NaPTAN data.

Revision ID: 028
Revises: 027
"""
from alembic import op
import sqlalchemy as sa

revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'transport_stops',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('atco_code', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('street', sa.String(200), nullable=True),
        sa.Column('locality_name', sa.String(100), nullable=True),
        sa.Column('town', sa.String(100), nullable=True),
        sa.Column('stop_type', sa.String(10), nullable=True, index=True),
        sa.Column('bus_stop_type', sa.String(10), nullable=True),
        sa.Column('bearing', sa.String(5), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('easting', sa.Integer(), nullable=True),
        sa.Column('northing', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(10), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_transport_lat_lng', 'transport_stops', ['latitude', 'longitude'])


def downgrade():
    op.drop_table('transport_stops')
