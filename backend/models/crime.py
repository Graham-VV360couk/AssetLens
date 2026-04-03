"""Crime model — stores UK police street-level crime data."""
from sqlalchemy import Column, Integer, String, Float, Date, Index
from .base import Base, TimestampMixin


class Crime(Base, TimestampMixin):
    """
    Street-level crime record sourced from data.police.uk bulk CSV exports.
    Indexed by LSOA and coordinates for proximity queries against properties.
    """
    __tablename__ = 'crimes'

    id              = Column(Integer, primary_key=True)
    crime_id        = Column(String(70), nullable=True, index=True)   # hash; null for ASB
    month           = Column(Date, nullable=False, index=True)        # first of month
    latitude        = Column(Float, nullable=True)
    longitude       = Column(Float, nullable=True)
    location        = Column(String(200), nullable=True)
    falls_within    = Column(String(100), nullable=True)
    lsoa_code       = Column(String(15), nullable=True, index=True)
    lsoa_name       = Column(String(100), nullable=True)
    crime_type      = Column(String(50), nullable=False, index=True)
    last_outcome    = Column(String(100), nullable=True)

    __table_args__ = (
        Index('ix_crime_lsoa_month', 'lsoa_code', 'month'),
        Index('ix_crime_lat_lng', 'latitude', 'longitude'),
        Index('ix_crime_type_month', 'crime_type', 'month'),
    )

    def __repr__(self):
        return f"<Crime(id={self.id}, type='{self.crime_type}', month='{self.month}')>"
