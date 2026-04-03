"""Private sale listing and messaging models."""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class PrivateListing(Base, TimestampMixin):
    """A property listed for private sale by its owner."""
    __tablename__ = 'private_listings'

    id              = Column(Integer, primary_key=True)
    user_property_id = Column(Integer, ForeignKey('user_properties.id', ondelete='CASCADE'), index=True, nullable=False)
    seller_id       = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    property_id     = Column(Integer, ForeignKey('properties.id', ondelete='SET NULL'), nullable=True, index=True)
    asking_price    = Column(Float, nullable=False)
    description     = Column(Text, nullable=True)
    photos_json     = Column(Text, nullable=True)
    status          = Column(String(20), default='active', nullable=False)

    seller = relationship('User', backref='private_listings')
    user_property = relationship('UserProperty', backref='listings')
    conversations = relationship('Conversation', back_populates='listing', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<PrivateListing(id={self.id}, price={self.asking_price}, status={self.status})>"


class Conversation(Base, TimestampMixin):
    """
    Double opt-in conversation between a buyer and seller.
    Both must opt in before messages can be exchanged.
    Identities are anonymous until parties choose to share details.
    """
    __tablename__ = 'conversations'

    id              = Column(Integer, primary_key=True)
    listing_id      = Column(Integer, ForeignKey('private_listings.id', ondelete='CASCADE'), index=True, nullable=False)
    buyer_id        = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    seller_id       = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    buyer_opted_in  = Column(Boolean, default=True, nullable=False)
    seller_opted_in = Column(Boolean, default=False, nullable=False)
    status          = Column(String(20), default='pending', nullable=False)  # pending, active, closed

    listing = relationship('PrivateListing', back_populates='conversations')
    buyer = relationship('User', foreign_keys=[buyer_id], backref='buyer_conversations')
    seller = relationship('User', foreign_keys=[seller_id], backref='seller_conversations')
    messages = relationship('Message', back_populates='conversation', cascade='all, delete-orphan',
                           order_by='Message.created_at')

    __table_args__ = (
        Index('ix_conversation_buyer_listing', 'buyer_id', 'listing_id', unique=True),
    )

    @property
    def is_active(self):
        return self.buyer_opted_in and self.seller_opted_in and self.status == 'active'

    def __repr__(self):
        return f"<Conversation(id={self.id}, status={self.status}, active={self.is_active})>"


class Message(Base):
    """A single message within a conversation."""
    __tablename__ = 'messages'

    id              = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'), index=True, nullable=False)
    sender_id       = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    body            = Column(Text, nullable=False)
    is_read         = Column(Boolean, default=False, nullable=False)
    created_at      = Column(DateTime, nullable=False)

    conversation = relationship('Conversation', back_populates='messages')

    def __repr__(self):
        return f"<Message(id={self.id}, conv={self.conversation_id})>"
