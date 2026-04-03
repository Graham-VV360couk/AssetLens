"""ONS Postcode Directory model — the glue table linking postcodes to all geographies."""
from sqlalchemy import Column, Integer, String, Float, SmallInteger, Index
from .base import Base, TimestampMixin


class Postcode(Base, TimestampMixin):
    """
    ONS Postcode Directory (ONSPD) record.
    Maps every UK postcode to coordinates, LSOA, MSOA, IMD, ward,
    local authority, region, police force area, and more.
    """
    __tablename__ = 'postcodes'

    id              = Column(Integer, primary_key=True)
    postcode        = Column(String(8), unique=True, nullable=False, index=True)  # pcds format
    date_introduced = Column(String(6), nullable=True)    # YYYYMM
    date_terminated = Column(String(6), nullable=True)    # YYYYMM or null if live
    latitude        = Column(Float, nullable=True)
    longitude       = Column(Float, nullable=True)
    easting         = Column(Integer, nullable=True)
    northing        = Column(Integer, nullable=True)
    grid_quality    = Column(SmallInteger, nullable=True)  # 1-9 positional quality indicator

    # Administrative geographies
    lad_code        = Column(String(9), nullable=True, index=True)   # local authority district
    ward_code       = Column(String(9), nullable=True)               # electoral ward
    county_code     = Column(String(9), nullable=True)               # county
    region_code     = Column(String(9), nullable=True, index=True)   # region (former GOR)
    country_code    = Column(String(9), nullable=True)               # E92/W92/S92/N92
    pcon_code       = Column(String(9), nullable=True)               # parliamentary constituency
    parish_code     = Column(String(9), nullable=True)               # civil parish

    # Census geographies
    oa21_code       = Column(String(9), nullable=True)               # 2021 output area
    lsoa11_code     = Column(String(9), nullable=True, index=True)   # 2011 LSOA
    lsoa21_code     = Column(String(9), nullable=True, index=True)   # 2021 LSOA
    msoa11_code     = Column(String(9), nullable=True)               # 2011 MSOA
    msoa21_code     = Column(String(9), nullable=True)               # 2021 MSOA

    # Deprivation & classification
    imd_rank        = Column(Integer, nullable=True, index=True)     # 1 = most deprived
    rural_urban     = Column(String(2), nullable=True)               # 2011 RUC
    oac11           = Column(String(3), nullable=True)               # output area classification

    # Police & health
    pfa_code        = Column(String(9), nullable=True, index=True)   # police force area
    icb_code        = Column(String(9), nullable=True)               # integrated care board

    __table_args__ = (
        Index('ix_postcode_pcds', 'postcode'),
        Index('ix_postcode_lsoa11', 'lsoa11_code'),
        Index('ix_postcode_lsoa21', 'lsoa21_code'),
        Index('ix_postcode_lad', 'lad_code'),
        Index('ix_postcode_imd', 'imd_rank'),
        Index('ix_postcode_pfa', 'pfa_code'),
        Index('ix_postcode_lat_lng', 'latitude', 'longitude'),
    )

    @property
    def is_live(self) -> bool:
        return self.date_terminated is None

    def __repr__(self):
        status = 'live' if self.is_live else f'terminated {self.date_terminated}'
        return f"<Postcode('{self.postcode}', {status})>"
