"""
Property core models
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class Property(Base, TimestampMixin):
    """
    Core property records with investment tracking
    """
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True, index=True)

    # Address details
    address = Column(String(500), nullable=False)
    postcode = Column(String(10), nullable=False, index=True)
    town = Column(String(100))
    county = Column(String(100))

    # Property characteristics
    property_type = Column(String(50), nullable=False)  # detached, semi-detached, terraced, flat, etc.
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    reception_rooms = Column(Integer)

    # Property size
    floor_area_sqm = Column(Float)
    plot_size_sqm = Column(Float)

    # Financial details
    asking_price = Column(Float)
    price_qualifier = Column(String(20))  # offers over, guide price, fixed price, etc.

    # Status tracking
    status = Column(String(20), default='active', nullable=False, index=True)  # active, archived, sold
    date_found = Column(Date, default=datetime.utcnow, nullable=False, index=True)
    date_sold = Column(Date)

    # Review tracking (6-month suppression)
    is_reviewed = Column(Boolean, default=False, nullable=False)
    reviewed_at = Column(DateTime)

    # Description
    description = Column(Text)

    # Relationships
    sources = relationship('PropertySource', back_populates='property', cascade='all, delete-orphan')
    sales_history = relationship('SalesHistory', back_populates='property', cascade='all, delete-orphan')
    rentals = relationship('Rental', back_populates='property', cascade='all, delete-orphan')
    hmo_records = relationship('HMORegister', back_populates='property', cascade='all, delete-orphan')
    auctions = relationship('Auction', back_populates='property', cascade='all, delete-orphan')
    score = relationship('PropertyScore', back_populates='property', cascade='all, delete-orphan', uselist=False)

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_property_postcode_type_status', 'postcode', 'property_type', 'status'),
        Index('ix_property_status_date_found', 'status', 'date_found'),
        Index('ix_property_reviewed', 'is_reviewed', 'reviewed_at'),
    )

    def __repr__(self):
        return f"<Property(id={self.id}, address='{self.address}', postcode='{self.postcode}')>"


class PropertySource(Base, TimestampMixin):
    """
    Track all sources for each property to support deduplication and multi-source tracking
    """
    __tablename__ = 'property_sources'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False, index=True)

    # Source details
    source_name = Column(String(50), nullable=False)  # searchland, rightmove, zoopla, auction, etc.
    source_id = Column(String(100))  # External ID from source system
    source_url = Column(String(1000))

    # Import tracking
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship
    property = relationship('Property', back_populates='sources')

    __table_args__ = (
        Index('ix_source_name_id', 'source_name', 'source_id'),
        Index('ix_source_active', 'is_active', 'last_seen_at'),
    )

    def __repr__(self):
        return f"<PropertySource(property_id={self.property_id}, source='{self.source_name}')>"


class PropertyScore(Base, TimestampMixin):
    """
    Calculated investment scores and valuations
    """
    __tablename__ = 'property_scores'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False, unique=True, index=True)

    # Valuation
    estimated_value = Column(Float)
    valuation_confidence = Column(Float)  # 0-1 confidence score

    # Price metrics
    price_deviation_pct = Column(Float)  # (estimated - asking) / estimated * 100
    price_score = Column(Float)  # 0-100 score based on price deviation

    # Yield metrics
    estimated_monthly_rent = Column(Float)
    gross_yield_pct = Column(Float)
    yield_score = Column(Float)  # 0-100 score based on yield

    # Area metrics
    area_trend_score = Column(Float)  # 0-100 score based on 10-year growth
    area_avg_price = Column(Float)
    area_growth_10yr_pct = Column(Float)

    # Composite score
    investment_score = Column(Float, index=True)  # 0-100 weighted composite score
    price_band = Column(String(20))  # brilliant, good, fair, bad

    # HMO opportunity
    hmo_opportunity_score = Column(Float)  # 0-100 if applicable

    # Calculation metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_version = Column(String(20))

    # Relationship
    property = relationship('Property', back_populates='score')

    __table_args__ = (
        Index('ix_score_investment', 'investment_score'),
        Index('ix_score_yield', 'yield_score'),
        Index('ix_score_price_band', 'price_band'),
        Index('ix_score_calculated_at', 'calculated_at'),
    )

    def __repr__(self):
        return f"<PropertyScore(property_id={self.property_id}, score={self.investment_score})>"
