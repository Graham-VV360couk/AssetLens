"""Planning designation model — stores planning.data.gov.uk geographic constraints."""
from sqlalchemy import Column, Integer, String, Float, Date, Text, Index
from .base import Base, TimestampMixin


class PlanningDesignation(Base, TimestampMixin):
    """
    Planning constraint/designation from planning.data.gov.uk.
    Each record represents a geographic area with a specific planning designation
    (conservation area, listed building, flood risk zone, Article 4, etc.).
    Uses a unified schema with dataset-specific fields stored in extra columns.
    """
    __tablename__ = 'planning_designations'

    id              = Column(Integer, primary_key=True)
    dataset         = Column(String(60), nullable=False, index=True)
    entity          = Column(Integer, nullable=False, index=True)     # planning.data.gov.uk entity ID
    name            = Column(String(500), nullable=True)
    reference       = Column(String(200), nullable=True, index=True)
    organisation    = Column(String(200), nullable=True)
    start_date      = Column(Date, nullable=True)
    end_date        = Column(Date, nullable=True)
    entry_date      = Column(Date, nullable=True)

    # Point coordinates (extracted from POINT WKT)
    latitude        = Column(Float, nullable=True)
    longitude       = Column(Float, nullable=True)

    # Dataset-specific fields (populated where relevant)
    listed_building_grade   = Column(String(5), nullable=True)    # I, II, II*
    flood_risk_level        = Column(String(10), nullable=True)   # 2, 3a, 3b
    flood_risk_type         = Column(String(50), nullable=True)   # Tidal, Fluvial, etc.
    permitted_dev_rights    = Column(Text, nullable=True)         # Article 4 removed rights
    description             = Column(Text, nullable=True)         # Article 4 / TPZ description
    hectares                = Column(Float, nullable=True)        # Brownfield site area
    max_net_dwellings       = Column(Integer, nullable=True)      # Brownfield potential
    min_net_dwellings       = Column(Integer, nullable=True)      # Brownfield potential
    designation_date        = Column(Date, nullable=True)         # Conservation area
    ancient_woodland_status = Column(String(100), nullable=True)
    heritage_at_risk        = Column(String(200), nullable=True)
    notes                   = Column(Text, nullable=True)

    __table_args__ = (
        Index('ix_planning_dataset', 'dataset'),
        Index('ix_planning_entity', 'entity'),
        Index('ix_planning_dataset_entity', 'dataset', 'entity', unique=True),
        Index('ix_planning_lat_lng', 'latitude', 'longitude'),
        Index('ix_planning_reference', 'reference'),
    )

    def __repr__(self):
        return f"<PlanningDesignation(dataset='{self.dataset}', name='{self.name}')>"
