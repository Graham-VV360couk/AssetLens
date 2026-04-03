"""Create schools table for DfE GIAS data.

Revision ID: 024
Revises: 023
"""
from alembic import op
import sqlalchemy as sa

revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'schools',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('urn', sa.Integer(), unique=True, index=True, nullable=False),
        sa.Column('la_name', sa.String(100)),
        sa.Column('establishment_name', sa.String(200), nullable=False),
        sa.Column('type_of_establishment', sa.String(100)),
        sa.Column('phase_of_education', sa.String(50)),
        sa.Column('statutory_low_age', sa.Integer(), nullable=True),
        sa.Column('statutory_high_age', sa.Integer(), nullable=True),
        sa.Column('is_boarding', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('nursery_provision', sa.String(50), nullable=True),
        sa.Column('has_sixth_form', sa.String(50), nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('religious_character', sa.String(100), nullable=True),
        sa.Column('is_selective', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('school_capacity', sa.Integer(), nullable=True),
        sa.Column('number_of_pupils', sa.Integer(), nullable=True),
        sa.Column('number_of_boys', sa.Integer(), nullable=True),
        sa.Column('number_of_girls', sa.Integer(), nullable=True),
        sa.Column('street', sa.String(200), nullable=True),
        sa.Column('locality', sa.String(200), nullable=True),
        sa.Column('address3', sa.String(200), nullable=True),
        sa.Column('town', sa.String(100), nullable=True),
        sa.Column('county', sa.String(100), nullable=True),
        sa.Column('postcode', sa.String(10), index=True, nullable=True),
        sa.Column('school_website', sa.String(500), nullable=True),
        sa.Column('telephone_num', sa.String(30), nullable=True),
        sa.Column('head_title', sa.String(20), nullable=True),
        sa.Column('head_first_name', sa.String(100), nullable=True),
        sa.Column('head_last_name', sa.String(100), nullable=True),
        sa.Column('easting', sa.Integer(), nullable=True),
        sa.Column('northing', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('schools')
