"""Pydantic v2 schemas for AssetLens API."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class SalesHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_date: Optional[datetime]
    sale_price: Optional[int]
    property_type: Optional[str]
    address: Optional[str]
    postcode: Optional[str]


class PropertyScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    estimated_value: Optional[float]
    valuation_confidence: Optional[float]
    price_deviation_pct: Optional[float]
    price_score: Optional[float]
    estimated_monthly_rent: Optional[float]
    gross_yield_pct: Optional[float]
    yield_score: Optional[float]
    area_trend_score: Optional[float]
    area_avg_price: Optional[float]
    area_growth_10yr_pct: Optional[float]
    investment_score: Optional[float]
    price_band: Optional[str]
    hmo_opportunity_score: Optional[float]
    hmo_gross_yield_pct: Optional[float]
    pd_avm: Optional[float]
    pd_avm_lower: Optional[float]
    pd_avm_upper: Optional[float]
    pd_rental_estimate: Optional[float]
    pd_flood_risk: Optional[str]
    pd_enriched_at: Optional[datetime]
    calculated_at: Optional[datetime]


class PropertySourceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_name: Optional[str]
    source_url: Optional[str]
    is_active: Optional[bool]
    last_seen_at: Optional[datetime]


class AuctionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    auctioneer: Optional[str]
    auction_date: Optional[datetime]
    lot_number: Optional[str]
    guide_price: Optional[int]
    reserve_price: Optional[int]
    sold_price: Optional[int]
    is_sold: Optional[bool]
    sale_status: Optional[str]
    auction_house_url: Optional[str]


class PropertyAIInsightSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    verdict: Optional[str]
    confidence: Optional[float]
    summary: Optional[str]
    location_notes: Optional[str]
    positives: Optional[str]   # JSON text
    risks: Optional[str]       # JSON text
    tokens_used: Optional[int]
    generated_at: Optional[datetime]


class PropertySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    address: str
    postcode: Optional[str]
    town: Optional[str]
    county: Optional[str]
    property_type: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    asking_price: Optional[int]
    status: Optional[str]
    date_found: Optional[datetime]
    is_reviewed: Optional[bool]
    image_url: Optional[str]
    score: Optional[PropertyScoreSchema]
    ai_insight: Optional[PropertyAIInsightSchema]
    # Populated only when radius search is active
    distance_miles: Optional[float] = None


class PropertyDetail(PropertySummary):
    description: Optional[str]
    floor_area_sqm: Optional[float]
    sources: List[PropertySourceSchema] = []
    sales_history: List[SalesHistoryItem] = []
    auctions: List[AuctionSchema] = []
    # EPC cache fields
    epc_energy_rating:        Optional[str] = None
    epc_potential_rating:     Optional[str] = None
    epc_floor_area_sqm:       Optional[float] = None
    epc_inspection_date:      Optional[datetime] = None
    epc_matched_at:           Optional[datetime] = None
    epc_compliance_cost_low:  Optional[int] = None
    epc_compliance_cost_high: Optional[int] = None


class PropertyListResponse(BaseModel):
    items: List[PropertySummary]
    total: int
    page: int
    page_size: int
    pages: int


class AreaStats(BaseModel):
    postcode_district: str
    avg_price_1yr: Optional[float] = None
    avg_price_3yr: Optional[float] = None
    avg_price_5yr: Optional[float] = None
    avg_price_10yr: Optional[float] = None
    growth_pct_10yr: Optional[float] = None
    growth_pct_5yr: Optional[float] = None
    transaction_count_1yr: Optional[int] = None
    transaction_count_10yr: Optional[int] = None
    sales_by_year: List[dict] = []


class ReviewResponse(BaseModel):
    property_id: int
    is_reviewed: bool
    reviewed_at: Optional[datetime]
    message: str


class DashboardStats(BaseModel):
    total_active: int
    total_reviewed: int
    high_value_count: int
    avg_investment_score: Optional[float]
    avg_yield: Optional[float]
    by_price_band: dict
    by_property_type: dict
    score_distribution: List[dict] = []
    recent_high_value: List[PropertySummary] = []
