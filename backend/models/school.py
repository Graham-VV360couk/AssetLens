"""School model — stores DfE GIAS school data for proximity analysis."""
from sqlalchemy import Column, Integer, String, Boolean, Index
from .base import Base, TimestampMixin


class School(Base, TimestampMixin):
    """
    School record sourced from DfE Get Information About Schools (GIAS) bulk export.
    Indexed by postcode for fast proximity lookups against properties.
    """
    __tablename__ = 'schools'

    id                  = Column(Integer, primary_key=True)
    urn                 = Column(Integer, unique=True, index=True, nullable=False)
    la_name             = Column(String(100))
    establishment_name  = Column(String(200), nullable=False)
    type_of_establishment = Column(String(100))
    phase_of_education  = Column(String(50))
    statutory_low_age   = Column(Integer, nullable=True)
    statutory_high_age  = Column(Integer, nullable=True)
    is_boarding         = Column(Boolean, default=False)
    nursery_provision   = Column(String(50), nullable=True)
    has_sixth_form      = Column(String(50), nullable=True)
    gender              = Column(String(20), nullable=True)
    religious_character = Column(String(100), nullable=True)
    is_selective        = Column(Boolean, default=False)
    school_capacity     = Column(Integer, nullable=True)
    number_of_pupils    = Column(Integer, nullable=True)
    number_of_boys      = Column(Integer, nullable=True)
    number_of_girls     = Column(Integer, nullable=True)
    street              = Column(String(200), nullable=True)
    locality            = Column(String(200), nullable=True)
    address3            = Column(String(200), nullable=True)
    town                = Column(String(100), nullable=True)
    county              = Column(String(100), nullable=True)
    postcode            = Column(String(10), index=True, nullable=True)
    school_website      = Column(String(500), nullable=True)
    telephone_num       = Column(String(30), nullable=True)
    head_title          = Column(String(20), nullable=True)
    head_first_name     = Column(String(100), nullable=True)
    head_last_name      = Column(String(100), nullable=True)
    easting             = Column(Integer, nullable=True)
    northing            = Column(Integer, nullable=True)

    __table_args__ = (
        Index('ix_schools_postcode', 'postcode'),
        Index('ix_schools_urn', 'urn'),
    )

    def __repr__(self):
        return f"<School(urn={self.urn}, name='{self.establishment_name}')>"
