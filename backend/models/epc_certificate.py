"""EPC Certificate model — stores bulk EPC data for fast local lookups."""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Index
from datetime import datetime
from .base import Base, TimestampMixin


class EPCCertificate(Base, TimestampMixin):
    """
    EPC certificate record sourced from the EPC bulk download.
    Indexed by postcode for fast address matching.
    """
    __tablename__ = 'epc_certificates'

    id              = Column(Integer, primary_key=True)
    lmk_key         = Column(String(100), unique=True, index=True)  # certificate ID
    address1        = Column(String(200))
    address2        = Column(String(200))
    postcode        = Column(String(10), index=True)
    uprn            = Column(String(20), index=True, nullable=True)
    property_type   = Column(String(50))   # House, Flat, Maisonette, Bungalow
    built_form      = Column(String(50))   # Detached, Semi-Detached, Mid-Terrace, End-Terrace
    floor_area_sqm          = Column(Float)
    energy_rating           = Column(String(5))
    potential_energy_rating = Column(String(5), nullable=True)
    inspection_date         = Column(Date)

    __table_args__ = (
        Index('ix_epc_postcode', 'postcode'),
        Index('ix_epc_uprn', 'uprn'),
    )

    def __repr__(self):
        return f"<EPCCertificate(lmk_key='{self.lmk_key}', postcode='{self.postcode}')>"
