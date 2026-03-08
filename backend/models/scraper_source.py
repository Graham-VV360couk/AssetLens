"""Scraper source configuration model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from .base import Base, TimestampMixin


class ScraperSource(Base, TimestampMixin):
    """User-configured URLs to scrape for property listings."""
    __tablename__ = 'scraper_sources'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(1000), nullable=False)
    source_type = Column(String(50), default='auction')  # auction, estate_agent, rental
    is_active = Column(Boolean, default=True, nullable=False)
    max_pages = Column(Integer, default=5)
    notes = Column(Text)

    # Run tracking
    last_run_at = Column(DateTime)
    last_run_status = Column(String(20))  # success, error, running, pending
    last_run_properties = Column(Integer, default=0)
    last_error = Column(Text)
    total_properties_found = Column(Integer, default=0)

    # Site investigation
    investigation_status = Column(String(20))  # pending, running, done, error
    investigation_ran_at = Column(DateTime)
    investigation_data = Column(Text)  # JSON blob of findings

    def __repr__(self):
        return f"<ScraperSource(name='{self.name}', url='{self.url}')>"
