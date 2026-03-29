"""Make sales_history.sale_price nullable for feed-sourced sold events

Revision ID: 020
Revises: 019
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'sales_history',
        'sale_price',
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade():
    # Set any nulls to 0 before making NOT NULL again
    op.execute("UPDATE sales_history SET sale_price = 0 WHERE sale_price IS NULL")
    op.alter_column(
        'sales_history',
        'sale_price',
        existing_type=sa.Float(),
        nullable=False,
    )
