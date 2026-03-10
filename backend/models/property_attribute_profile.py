"""Property Attribute Profile model — stores computed + user-override attribute estimates."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class PropertyAttributeProfile(Base, TimestampMixin):
    """
    Stores the computed property attribute profile for a property.

    Three payloads coexist:
    - computed_payload: raw engine output (never overwritten by user edits)
    - override_payload: user corrections keyed by field name
    - display_payload: merged result (overrides win) — this is what the UI shows
    """
    __tablename__ = 'property_attribute_profiles'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False, unique=True, index=True)

    # Estimation payloads (all JSON-encoded text)
    computed_payload = Column(Text)    # engine output — immutable after generation
    override_payload = Column(Text)    # user overrides: {field: override_value, ...}
    display_payload = Column(Text)     # merged: overrides take priority over computed
    source_summary = Column(Text)      # available input facts at time of computation
    debug_payload = Column(Text)       # warnings, contradiction notes, raw evidence

    # Metadata
    version = Column(Integer, default=1, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    generated_by = Column(String(50), default='system', nullable=False)

    property = relationship('Property', back_populates='attribute_profile')

    __table_args__ = (
        Index('ix_attr_profile_property_id', 'property_id'),
        Index('ix_attr_profile_generated_at', 'generated_at'),
    )

    def __repr__(self):
        return f"<PropertyAttributeProfile(property_id={self.property_id}, v={self.version})>"
