"""
Land Registry sales history model
"""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class SalesHistory(Base, TimestampMixin):
    """
    Historical Land Registry Price Paid Data
    10-year lookback for valuation and area trend analysis
    """
    __tablename__ = 'sales_history'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True, index=True)  # Nullable for bulk imports

    # Sale details
    sale_date = Column(Date, nullable=False, index=True)
    sale_price = Column(Float, nullable=False)

    # Address (for matching before property_id assignment)
    address = Column(String(500), nullable=False)
    postcode = Column(String(10), nullable=False, index=True)
    town = Column(String(100))
    county = Column(String(100))

    # Property details from Land Registry
    property_type = Column(String(50), nullable=False)  # D, S, T, F (Detached, Semi, Terraced, Flat)
    old_new = Column(String(1))  # Y (new build) or N (established)
    duration = Column(String(1))  # F (freehold) or L (leasehold)

    # Transaction details
    ppd_category_type = Column(String(1))  # A (standard), B (additional price paid)
    record_status = Column(String(1))  # A (addition), C (change), D (delete)

    # Land Registry unique identifier
    transaction_id = Column(String(100), unique=True, index=True)

    # Relationship
    property = relationship('Property', back_populates='sales_history')

    __table_args__ = (
        Index('ix_sales_postcode_date', 'postcode', 'sale_date'),
        Index('ix_sales_postcode_type', 'postcode', 'property_type'),
        Index('ix_sales_date_price', 'sale_date', 'sale_price'),
    )

    def __repr__(self):
        return f"<SalesHistory(postcode='{self.postcode}', date={self.sale_date}, price=£{self.sale_price})>"
