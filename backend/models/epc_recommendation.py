"""EPC Recommendation model — improvement items linked to EPC certificates."""
from sqlalchemy import Column, Integer, String, Float, Text, Index, ForeignKey
from .base import Base, TimestampMixin


class EPCRecommendation(Base, TimestampMixin):
    """
    EPC improvement recommendation sourced from the recommendations bulk download.
    Each certificate can have 5-15 rows. Linked by lmk_key.
    """
    __tablename__ = 'epc_recommendations'

    id                       = Column(Integer, primary_key=True)
    lmk_key                  = Column(String(100), nullable=False, index=True)
    improvement_item         = Column(String(100))   # short code / name
    improvement_summary_text = Column(String(500))   # one-liner description
    improvement_descr_text   = Column(Text)          # full description
    indicative_cost_raw      = Column(String(100))   # e.g. "£500 - £1,500"
    indicative_cost_low      = Column(Integer)        # parsed lower bound (£)
    indicative_cost_high     = Column(Integer)        # parsed upper bound (£)

    # Extended fields (Sprint 1 addendum)
    typical_saving              = Column(Float, nullable=True)       # annual £ saving
    efficiency_rating_before    = Column(Integer, nullable=True)     # EPC score before improvement
    efficiency_rating_after     = Column(Integer, nullable=True)     # EPC score after improvement

    __table_args__ = (
        Index('ix_epc_rec_lmk_key', 'lmk_key'),
    )

    def __repr__(self):
        return f"<EPCRecommendation(lmk_key='{self.lmk_key}', item='{self.improvement_item}')>"
