"""
Auction property model
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Auction(Base, TimestampMixin):
    """
    Property auction listings
    Supplementary data source for below-market opportunities
    """
    __tablename__ = 'auctions'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False, index=True)

    # Auction details
    auction_date = Column(DateTime, nullable=False, index=True)
    auctioneer = Column(String(100), nullable=False)
    auction_house_url = Column(String(500))
    lot_number = Column(String(50))

    # Pricing
    guide_price = Column(Float)
    reserve_price = Column(Float)
    sold_price = Column(Float)

    # Sale status
    is_sold = Column(Boolean, default=False)
    sale_status = Column(String(50))  # sold, unsold, withdrawn, postponed

    # Legal pack
    legal_pack_url = Column(String(1000))
    legal_pack_downloaded = Column(Boolean, default=False)

    # Auction description
    description = Column(Text)
    tenure = Column(String(50))  # freehold, leasehold
    viewing_date = Column(DateTime)

    # External reference
    auction_reference = Column(String(100), unique=True)

    # Relationship
    property = relationship('Property', back_populates='auctions')

    __table_args__ = (
        Index('ix_auction_date_status', 'auction_date', 'is_sold'),
        Index('ix_auction_auctioneer', 'auctioneer', 'auction_date'),
    )

    def __repr__(self):
        return f"<Auction(lot={self.lot_number}, auctioneer='{self.auctioneer}', date={self.auction_date})>"
