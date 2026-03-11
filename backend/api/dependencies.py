"""FastAPI dependency injection."""
import os
import redis
from typing import Generator, Optional
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.models.base import SessionLocal

# Redis connection
_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PropertyFilters:
    def __init__(
        self,
        postcode: Optional[str] = Query(None, description="Postcode prefix filter (comma-separated)"),
        town: Optional[str] = Query(None),
        county: Optional[str] = Query(None),
        property_type: Optional[str] = Query(None, description="detached|semi-detached|terraced|flat"),
        min_beds: Optional[int] = Query(None, ge=1, le=10),
        max_beds: Optional[int] = Query(None, ge=1, le=10),
        min_price: Optional[int] = Query(None, ge=0),
        max_price: Optional[int] = Query(None, ge=0),
        min_score: Optional[float] = Query(None, ge=0, le=100),
        min_yield: Optional[float] = Query(None, ge=0),
        price_band: Optional[str] = Query(None, description="brilliant|good|fair|bad"),
        source: Optional[str] = Query(None, description="Filter by scraper source name"),
        status: Optional[str] = Query('active'),
        is_reviewed: Optional[bool] = Query(None),
        sort_by: str = Query('investment_score', description="investment_score|asking_price|date_found|yield"),
        sort_dir: str = Query('desc', description="asc|desc"),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        # Radius search (mutually exclusive with postcode chips)
        center_postcode: Optional[str] = Query(None, description="Center postcode for radius search"),
        radius_miles: Optional[float] = Query(None, ge=0.5, le=100, description="Radius in miles"),
    ):
        self.postcode = postcode
        self.town = town
        self.county = county
        self.property_type = property_type
        self.min_beds = min_beds
        self.max_beds = max_beds
        self.min_price = min_price
        self.max_price = max_price
        self.min_score = min_score
        self.min_yield = min_yield
        self.price_band = price_band
        self.source = source
        self.status = status
        self.is_reviewed = is_reviewed
        self.sort_by = sort_by
        self.sort_dir = sort_dir
        self.page = page
        self.page_size = page_size
        self.center_postcode = center_postcode
        self.radius_miles = radius_miles
