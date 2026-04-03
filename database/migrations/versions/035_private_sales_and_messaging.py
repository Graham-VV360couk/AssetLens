"""Create private_listings and messaging tables.

Revision ID: 035
Revises: 034
"""
from alembic import op
import sqlalchemy as sa

revision = '035'
down_revision = '034'
branch_labels = None
depends_on = None


def upgrade():
    # Private sale listings — created from user_properties with a valuation
    op.create_table(
        'private_listings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_property_id', sa.Integer(), sa.ForeignKey('user_properties.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('seller_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('asking_price', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('photos_json', sa.Text(), nullable=True),  # JSON array of photo URLs
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),  # active, under_offer, sold, withdrawn
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Conversations — double opt-in anonymous messaging
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('private_listings.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('buyer_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('seller_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('buyer_opted_in', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('seller_opted_in', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, active, closed
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_conversation_buyer_listing', 'conversations', ['buyer_id', 'listing_id'], unique=True)

    # Messages within conversations
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('sender_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('private_listings')
