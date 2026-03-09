"""Add property_ai_insights table

Revision ID: 007
Revises: 006
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'property_ai_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('verdict', sa.String(20), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('location_notes', sa.Text(), nullable=True),
        sa.Column('positives', sa.Text(), nullable=True),
        sa.Column('risks', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_property_ai_insights'),
        sa.UniqueConstraint('property_id', name='uq_ai_insight_property'),
    )
    op.create_index('ix_property_ai_insights_id', 'property_ai_insights', ['id'])
    op.create_index('ix_ai_insight_verdict', 'property_ai_insights', ['verdict'])
    op.create_index('ix_ai_insight_generated', 'property_ai_insights', ['generated_at'])


def downgrade():
    op.drop_table('property_ai_insights')
