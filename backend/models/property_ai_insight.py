"""AI-generated property investment analysis."""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class PropertyAIInsight(Base):
    __tablename__ = 'property_ai_insights'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)

    verdict = Column(String(20), nullable=False)   # STRONG_BUY | BUY | HOLD | AVOID
    summary = Column(Text)                          # 2-3 sentence overview
    location_notes = Column(Text)                   # What Claude knows about this area
    positives = Column(Text)                        # Bullet points (JSON array stored as text)
    risks = Column(Text)                            # Bullet points (JSON array stored as text)
    confidence = Column(Float)                      # 0-1

    property = relationship('Property', back_populates='ai_insight')

    model_used = Column(String(50), default='claude-sonnet-4-6')
    tokens_used = Column(Integer)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_ai_insight_verdict', 'verdict'),
        Index('ix_ai_insight_generated', 'generated_at'),
    )
