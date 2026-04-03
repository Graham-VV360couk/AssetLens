"""User property portfolio and valuation models."""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class UserProperty(Base, TimestampMixin):
    """A property owned/managed by a user — part of their portfolio."""
    __tablename__ = 'user_properties'

    id                      = Column(Integer, primary_key=True)
    user_id                 = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    address_line1           = Column(String(200), nullable=False)
    address_line2           = Column(String(200), nullable=True)
    town                    = Column(String(100), nullable=False)
    postcode                = Column(String(10), nullable=False, index=True)
    property_type           = Column(String(30), nullable=False)
    bedrooms                = Column(Integer, nullable=False)
    bathrooms               = Column(Integer, nullable=True)
    relationship_to_property = Column(String(30), nullable=False)
    tenure                  = Column(String(20), nullable=False)
    lease_years_remaining   = Column(Integer, nullable=True)

    user = relationship('User', backref='properties_owned')
    valuations = relationship('PropertyValuation', back_populates='user_property', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<UserProperty(id={self.id}, address='{self.address_line1}', postcode='{self.postcode}')>"


class PropertyValuation(Base):
    """Versioned valuation result — never overwritten, always appended."""
    __tablename__ = 'property_valuations'

    id                  = Column(Integer, primary_key=True)
    user_property_id    = Column(Integer, ForeignKey('user_properties.id', ondelete='CASCADE'), index=True, nullable=False)
    user_id             = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)

    answers_json        = Column(Text, nullable=False)  # all wizard answers

    avm_baseline        = Column(Float, nullable=True)
    avm_source          = Column(String(50), nullable=True)

    feature_adjustment  = Column(Float, nullable=True)
    condition_adjustment = Column(Float, nullable=True)
    situation_band      = Column(String(20), nullable=True)
    situation_band_pct  = Column(Float, nullable=True)

    range_low           = Column(Float, nullable=True)
    range_mid           = Column(Float, nullable=True)
    range_high          = Column(Float, nullable=True)

    created_at          = Column(DateTime, nullable=False)

    user_property = relationship('UserProperty', back_populates='valuations')

    def __repr__(self):
        return f"<PropertyValuation(id={self.id}, range=£{self.range_low}-£{self.range_high})>"
