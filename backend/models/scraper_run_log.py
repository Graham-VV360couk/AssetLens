"""Scraper run log model — per-message log entries for each scrape/investigation run."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from datetime import datetime
from .base import Base


class ScraperRunLog(Base):
    __tablename__ = 'scraper_run_logs'

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey('scraper_sources.id', ondelete='CASCADE'), nullable=False, index=True)
    run_id = Column(String(36), nullable=False, index=True)   # UUID per run
    run_type = Column(String(20), default='scrape')           # scrape | investigate
    level = Column(String(10), nullable=False, default='info')  # info | warning | error
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_run_log_source_run', 'source_id', 'run_id'),
        Index('ix_run_log_created', 'created_at'),
    )
