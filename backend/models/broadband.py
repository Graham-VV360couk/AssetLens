"""Broadband coverage model — stores Ofcom fixed broadband stats by postcode."""
from sqlalchemy import Column, Integer, String, Float, Index
from .base import Base, TimestampMixin


class BroadbandCoverage(Base, TimestampMixin):
    """
    Ofcom fixed broadband coverage statistics per postcode (residential premises).
    All percentage fields are 0-100.
    """
    __tablename__ = 'broadband_coverage'

    id                  = Column(Integer, primary_key=True)
    postcode            = Column(String(8), unique=True, nullable=False, index=True)

    # Speed tier availability (% of premises)
    sfbb_availability   = Column(Float, nullable=True)   # Superfast (>=30Mbit/s)
    ufbb_100_availability = Column(Float, nullable=True) # Ultrafast (>=100Mbit/s)
    ufbb_availability   = Column(Float, nullable=True)   # Ultrafast (>=300Mbit/s)
    gigabit_availability = Column(Float, nullable=True)  # Gigabit (>=1000Mbit/s)

    # Speed distribution (% of premises in each band)
    pct_below_2         = Column(Float, nullable=True)   # 0 to <2 Mbit/s
    pct_2_to_5          = Column(Float, nullable=True)   # 2 to <5 Mbit/s
    pct_5_to_10         = Column(Float, nullable=True)   # 5 to <10 Mbit/s
    pct_10_to_30        = Column(Float, nullable=True)   # 10 to <30 Mbit/s
    pct_30_to_300       = Column(Float, nullable=True)   # 30 to <300 Mbit/s
    pct_above_300       = Column(Float, nullable=True)   # >=300 Mbit/s

    # Unable to receive thresholds
    pct_unable_2        = Column(Float, nullable=True)
    pct_unable_5        = Column(Float, nullable=True)
    pct_unable_10       = Column(Float, nullable=True)
    pct_unable_30       = Column(Float, nullable=True)

    # Key indicators
    pct_below_uso       = Column(Float, nullable=True)   # Below Universal Service Obligation
    pct_nga             = Column(Float, nullable=True)    # Next Generation Access
    pct_fwa_decent      = Column(Float, nullable=True)   # Decent broadband from FWA

    __table_args__ = (
        Index('ix_broadband_postcode', 'postcode'),
    )

    def __repr__(self):
        return f"<BroadbandCoverage(postcode='{self.postcode}', gigabit={self.gigabit_availability}%)>"
