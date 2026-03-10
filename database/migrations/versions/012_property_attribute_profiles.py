"""Add property_attribute_profiles table

Revision ID: 012
Revises: 011
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'property_attribute_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id'), nullable=False),

        # Estimation payloads
        sa.Column('computed_payload', sa.Text(), nullable=True),
        sa.Column('override_payload', sa.Text(), nullable=True),
        sa.Column('display_payload', sa.Text(), nullable=True),
        sa.Column('source_summary', sa.Text(), nullable=True),
        sa.Column('debug_payload', sa.Text(), nullable=True),

        # Metadata
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('generated_by', sa.String(50), nullable=False, server_default='system'),

        # TimestampMixin
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_attr_profile_property_id', 'property_attribute_profiles', ['property_id'], unique=True)
    op.create_index('ix_attr_profile_generated_at', 'property_attribute_profiles', ['generated_at'])


def downgrade():
    op.drop_index('ix_attr_profile_generated_at', table_name='property_attribute_profiles')
    op.drop_index('ix_attr_profile_property_id', table_name='property_attribute_profiles')
    op.drop_table('property_attribute_profiles')
