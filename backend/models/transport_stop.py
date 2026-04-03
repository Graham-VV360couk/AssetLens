"""Transport stop model — stores NaPTAN public transport access points."""
from sqlalchemy import Column, Integer, String, Float, Index
from .base import Base, TimestampMixin


class TransportStop(Base, TimestampMixin):
    """
    Public transport stop/station from the NaPTAN (National Public Transport
    Access Nodes) dataset. Indexed by coordinates for proximity queries.
    """
    __tablename__ = 'transport_stops'

    id              = Column(Integer, primary_key=True)
    atco_code       = Column(String(20), unique=True, nullable=False, index=True)
    name            = Column(String(200), nullable=False)
    street          = Column(String(200), nullable=True)
    locality_name   = Column(String(100), nullable=True)
    town            = Column(String(100), nullable=True)
    stop_type       = Column(String(10), nullable=True, index=True)  # BCT, RLY, MET, etc.
    bus_stop_type   = Column(String(10), nullable=True)               # MKD, CUS, HAR, etc.
    bearing         = Column(String(5), nullable=True)
    latitude        = Column(Float, nullable=True)
    longitude       = Column(Float, nullable=True)
    easting         = Column(Integer, nullable=True)
    northing        = Column(Integer, nullable=True)
    status          = Column(String(10), nullable=True, index=True)   # active, inactive

    __table_args__ = (
        Index('ix_transport_atco', 'atco_code'),
        Index('ix_transport_lat_lng', 'latitude', 'longitude'),
        Index('ix_transport_type', 'stop_type'),
        Index('ix_transport_status', 'status'),
    )

    def __repr__(self):
        return f"<TransportStop(atco='{self.atco_code}', name='{self.name}', type='{self.stop_type}')>"
