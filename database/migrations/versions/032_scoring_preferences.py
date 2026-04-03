"""Add scoring_preferences to user_profiles.

Revision ID: 032
Revises: 031
"""
from alembic import op
import sqlalchemy as sa

revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_profiles', sa.Column('scoring_preferences', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('user_profiles', 'scoring_preferences')
