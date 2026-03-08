"""
HMO (House in Multiple Occupation) register model
"""

from sqlalchemy import Column, Integer, String, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class HMORegister(Base, TimestampMixin):
    """
    HMO licensing data from local councils
    Indicates properties with HMO potential
    """
    __tablename__ = 'hmo_registers'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True, index=True)

    # Licence details
    licence_number = Column(String(100), unique=True)
    licence_start = Column(Date, nullable=False)
    licence_expiry = Column(Date, nullable=False, index=True)
    licence_status = Column(String(20))  # active, expired, revoked

    # Property details
    address = Column(String(500), nullable=False)
    postcode = Column(String(10), nullable=False, index=True)

    # HMO specifics
    num_rooms = Column(Integer)
    max_occupants = Column(Integer)
    num_households = Column(Integer)

    # Council information
    council = Column(String(100), nullable=False, index=True)
    council_reference = Column(String(100))

    # Licence holder
    licence_holder_name = Column(String(200))

    # Relationship
    property = relationship('Property', back_populates='hmo_records')

    __table_args__ = (
        Index('ix_hmo_postcode_status', 'postcode', 'licence_status'),
        Index('ix_hmo_council_status', 'council', 'licence_status'),
        Index('ix_hmo_expiry', 'licence_expiry'),
    )

    def __repr__(self):
        return f"<HMORegister(postcode='{self.postcode}', rooms={self.num_rooms}, council='{self.council}')>"
