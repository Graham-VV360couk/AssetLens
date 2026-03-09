"""Scraper source configuration model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
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

    # Scraping options
    scrape_detail_pages = Column(Boolean, default=False)  # follow individual property links

    # Site investigation
    investigation_status = Column(String(20))  # pending, running, done, error
    investigation_ran_at = Column(DateTime)
    investigation_data = Column(Text)  # JSON blob of findings

    def __repr__(self):
        return f"<ScraperSource(name='{self.name}', url='{self.url}')>"


class ScraperStrategyLibrary(Base, TimestampMixin):
    """
    Library of proven scraping strategies, accumulated from successful scrapes.
    probe_id maps to a key in PROBE_REGISTRY (scrapers.py).
    domain is the netloc of the site it worked on (NULL = applies to all sites).
    As success_count grows for a probe, the investigation tries it earlier.
    """
    __tablename__ = 'scraper_strategy_library'

    id = Column(Integer, primary_key=True, index=True)
    probe_id = Column(String(100), nullable=False)
    domain = Column(String(200), nullable=True)   # NULL means globally useful
    success_count = Column(Integer, default=0, nullable=False)
    fail_count = Column(Integer, default=0, nullable=False)
    last_success_at = Column(DateTime, nullable=True)
    notes = Column(String(500), nullable=True)

    __table_args__ = (
        Index('ix_library_probe_domain', 'probe_id', 'domain', unique=True),
        Index('ix_library_success', 'success_count'),
    )

    def __repr__(self):
        return f"<ScraperStrategyLibrary(probe='{self.probe_id}', domain='{self.domain}', success={self.success_count})>"
