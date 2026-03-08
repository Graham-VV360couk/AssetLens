"""
Property Investment Scoring Service (Task #13)
Calculates composite investment scores for properties.
Score components:
- Price deviation score (0-40 pts): how far below estimated value
- Yield score (0-30 pts): gross rental yield
- Area trend score (0-20 pts): 10-year price growth
- HMO opportunity score (0-10 pts): HMO licensing potential
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.property import Property, PropertyScore
from backend.models.rental import Rental
from backend.models.sales_history import SalesHistory
from backend.models.hmo import HMORegister
from backend.ml.valuation_model import PropertyValuationModel

logger = logging.getLogger(__name__)

PRICE_BAND_THRESHOLDS = {
    'brilliant': -0.20,  # asking price >20% below estimate
    'good': -0.10,       # 10-20% below
    'fair': 0.05,        # within 5% of estimate
    'bad': float('inf'), # asking above estimate
}


@dataclass
class ScoringResult:
    estimated_value: Optional[float]
    valuation_confidence: float
    price_deviation_pct: Optional[float]
    price_score: float
    estimated_monthly_rent: Optional[float]
    gross_yield_pct: Optional[float]
    yield_score: float
    area_trend_score: float
    area_avg_price: Optional[float]
    area_growth_10yr_pct: Optional[float]
    investment_score: float
    price_band: str
    hmo_opportunity_score: float


class PropertyScoringService:
    def __init__(self, db: Session):
        self.db = db
        self.valuation_model = PropertyValuationModel()

    def score_property(self, prop: Property) -> ScoringResult:
        area_stats = self._get_area_stats(prop.postcode)

        # 1. ML Valuation
        estimated_value, confidence = self.valuation_model.predict(
            address=prop.address,
            postcode=prop.postcode,
            property_type=prop.property_type,
            bedrooms=prop.bedrooms,
            floor_area_sqm=prop.floor_area_sqm,
            area_stats=area_stats,
        )

        # 2. Price deviation
        price_deviation_pct = None
        price_score = 20.0  # neutral if no valuation
        if estimated_value and prop.asking_price and prop.asking_price > 0:
            price_deviation_pct = (prop.asking_price - estimated_value) / estimated_value
            price_score = self._calc_price_score(price_deviation_pct)

        # 3. Rental yield
        monthly_rent = self._estimate_rent(prop.postcode, prop.property_type, prop.bedrooms)
        gross_yield_pct = None
        yield_score = 10.0  # neutral if no data
        if monthly_rent and prop.asking_price and prop.asking_price > 0:
            gross_yield_pct = (monthly_rent * 12) / prop.asking_price * 100
            yield_score = self._calc_yield_score(gross_yield_pct)

        # 4. Area trend score
        area_trend_score = self._calc_area_trend_score(area_stats)
        area_growth_10yr = area_stats.get('growth_pct_10yr')

        # 5. HMO opportunity
        hmo_score = self._calc_hmo_score(prop)

        # 6. Composite score
        investment_score = price_score + yield_score + area_trend_score + hmo_score

        # 7. Price band
        price_band = self._classify_price_band(price_deviation_pct)

        return ScoringResult(
            estimated_value=estimated_value,
            valuation_confidence=confidence,
            price_deviation_pct=price_deviation_pct,
            price_score=price_score,
            estimated_monthly_rent=monthly_rent,
            gross_yield_pct=gross_yield_pct,
            yield_score=yield_score,
            area_trend_score=area_trend_score,
            area_avg_price=area_stats.get('avg_price_1yr'),
            area_growth_10yr_pct=area_growth_10yr,
            investment_score=min(100.0, max(0.0, investment_score)),
            price_band=price_band,
            hmo_opportunity_score=hmo_score,
        )

    def _calc_price_score(self, deviation: float) -> float:
        """0-40 points. More below estimated value = higher score."""
        if deviation <= -0.30:
            return 40.0
        elif deviation <= -0.20:
            return 35.0
        elif deviation <= -0.10:
            return 28.0
        elif deviation <= 0.0:
            return 20.0
        elif deviation <= 0.10:
            return 12.0
        elif deviation <= 0.20:
            return 6.0
        else:
            return 0.0

    def _calc_yield_score(self, gross_yield: float) -> float:
        """0-30 points. Higher yield = higher score."""
        if gross_yield >= 10.0:
            return 30.0
        elif gross_yield >= 8.0:
            return 25.0
        elif gross_yield >= 6.0:
            return 20.0
        elif gross_yield >= 5.0:
            return 15.0
        elif gross_yield >= 4.0:
            return 10.0
        elif gross_yield >= 3.0:
            return 5.0
        else:
            return 0.0

    def _calc_area_trend_score(self, area_stats: dict) -> float:
        """0-20 points. Based on 10-year price growth trend."""
        if 'growth_pct_10yr' not in area_stats:
            return 8.0  # neutral — no Land Registry data available
        growth_10yr = area_stats.get('growth_pct_10yr')
        if growth_10yr is None:
            return 8.0  # neutral
        if growth_10yr >= 0.80:
            return 20.0
        elif growth_10yr >= 0.50:
            return 17.0
        elif growth_10yr >= 0.30:
            return 14.0
        elif growth_10yr >= 0.15:
            return 10.0
        elif growth_10yr >= 0.0:
            return 6.0
        else:
            return 2.0

    def _calc_hmo_score(self, prop: Property) -> float:
        """0-10 points. HMO licensing potential."""
        if not prop.bedrooms or prop.bedrooms < 3:
            return 0.0

        # Check existing HMO licence
        existing_hmo = (
            self.db.query(HMORegister)
            .filter(HMORegister.postcode.like(f"{prop.postcode.split(' ')[0]}%"))
            .first()
        )

        if existing_hmo:
            return 8.0  # proven HMO area

        if prop.bedrooms >= 5:
            return 7.0
        elif prop.bedrooms >= 4:
            return 5.0
        elif prop.bedrooms >= 3:
            return 3.0
        return 0.0

    def _estimate_rent(
        self, postcode: str, property_type: Optional[str], bedrooms: Optional[int]
    ) -> Optional[float]:
        """Get estimated monthly rent from rental data or aggregates."""
        district = postcode.split(' ')[0] if ' ' in postcode else postcode[:4]

        # Try exact postcode first
        rental = (
            self.db.query(Rental)
            .filter(Rental.postcode.like(f"{district}%"), Rental.is_aggregated == True)
            .order_by(Rental.date_listed.desc())
            .first()
        )

        if rental and rental.rent_monthly:
            # Adjust for property size
            if bedrooms and rental.num_rooms:
                return float(rental.rent_per_room * bedrooms) if rental.rent_per_room else float(rental.rent_monthly)
            return float(rental.rent_monthly)

        # Fallback: national averages by type/beds
        fallback = {
            ('flat', 1): 950, ('flat', 2): 1300, ('flat', 3): 1600,
            ('terraced', 2): 1100, ('terraced', 3): 1350, ('terraced', 4): 1700,
            ('semi-detached', 3): 1400, ('semi-detached', 4): 1750,
            ('detached', 3): 1500, ('detached', 4): 1900, ('detached', 5): 2400,
        }
        key = (property_type or 'terraced', bedrooms or 3)
        return fallback.get(key, fallback.get(('terraced', 3), 1350))

    def _get_area_stats(self, postcode: str) -> dict:
        """Compute area price statistics from sales history."""
        district = postcode.split(' ')[0] if ' ' in postcode else postcode[:4]
        now = datetime.utcnow()

        stats = {}
        for years, key in [(1, '1yr'), (3, '3yr'), (5, '5yr'), (10, '10yr')]:
            cutoff = now - timedelta(days=365 * years)
            result = (
                self.db.query(
                    func.avg(SalesHistory.sale_price).label('avg'),
                    func.count(SalesHistory.id).label('cnt'),
                )
                .filter(
                    SalesHistory.postcode.like(f"{district}%"),
                    SalesHistory.sale_date >= cutoff,
                )
                .first()
            )
            if result and result.avg:
                stats[f'avg_price_{key}'] = float(result.avg)
                stats[f'transaction_count_{key}'] = int(result.cnt)

        # Growth rates
        if stats.get('avg_price_1yr') and stats.get('avg_price_10yr'):
            stats['growth_pct_10yr'] = (stats['avg_price_1yr'] - stats['avg_price_10yr']) / stats['avg_price_10yr']
        if stats.get('avg_price_1yr') and stats.get('avg_price_5yr'):
            stats['growth_pct_5yr'] = (stats['avg_price_1yr'] - stats['avg_price_5yr']) / stats['avg_price_5yr']

        stats['avg_price_1yr'] = stats.get('avg_price_1yr')
        stats['transaction_count'] = stats.get('transaction_count_1yr', 0)

        return stats

    def _classify_price_band(self, deviation: Optional[float]) -> str:
        if deviation is None:
            return 'unknown'
        if deviation <= PRICE_BAND_THRESHOLDS['brilliant']:
            return 'brilliant'
        elif deviation <= PRICE_BAND_THRESHOLDS['good']:
            return 'good'
        elif deviation <= PRICE_BAND_THRESHOLDS['fair']:
            return 'fair'
        else:
            return 'bad'


def save_score(db: Session, prop: Property, result: ScoringResult):
    """Upsert PropertyScore record."""
    score = db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()
    if not score:
        score = PropertyScore(property_id=prop.id)
        db.add(score)

    score.estimated_value = result.estimated_value
    score.valuation_confidence = result.valuation_confidence
    score.price_deviation_pct = result.price_deviation_pct
    score.price_score = result.price_score
    score.estimated_monthly_rent = result.estimated_monthly_rent
    score.gross_yield_pct = result.gross_yield_pct
    score.yield_score = result.yield_score
    score.area_trend_score = result.area_trend_score
    score.area_avg_price = result.area_avg_price
    score.area_growth_10yr_pct = result.area_growth_10yr_pct
    score.investment_score = result.investment_score
    score.price_band = result.price_band
    score.hmo_opportunity_score = result.hmo_opportunity_score
    score.calculated_at = datetime.utcnow()
    score.model_version = '1.0'
