"""
Rental data model
"""

from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Rental(Base, TimestampMixin):
    """
    Rental listings and postcode-level rental averages
    Used for gross yield calculations
    """
    __tablename__ = 'rentals'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True, index=True)  # Nullable for aggregated data

    # Rental details
    rent_monthly = Column(Float, nullable=False)
    rent_per_room = Column(Float)  # For HMO analysis

    # Property details
    postcode = Column(String(10), nullable=False, index=True)
    address = Column(String(500))
    property_type = Column(String(50))
    bedrooms = Column(Integer)
    num_rooms = Column(Integer)  # For HMO properties

    # Listing details
    date_listed = Column(Date, nullable=False, index=True)
    source = Column(String(50))  # spareroom, openrent, searchland, etc.
    source_url = Column(String(1000))
    is_hmo = Column(Boolean, default=False)

    # Aggregation flag
    is_aggregated = Column(Boolean, default=False)  # True for postcode-level averages

    # Relationship
    property = relationship('Property', back_populates='rentals')

    __table_args__ = (
        Index('ix_rental_postcode_date', 'postcode', 'date_listed'),
        Index('ix_rental_postcode_type', 'postcode', 'property_type'),
        Index('ix_rental_aggregated', 'is_aggregated', 'postcode'),
    )

    def __repr__(self):
        return f"<Rental(postcode='{self.postcode}', rent=£{self.rent_monthly}/mo)>"
