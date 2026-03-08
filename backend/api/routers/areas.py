"""Area statistics API endpoints."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.api.schemas import AreaStats
from backend.models.sales_history import SalesHistory

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/areas', tags=['areas'])


def _get_area_stats(db: Session, district: str) -> dict:
    now = datetime.utcnow()
    stats = {'postcode_district': district}

    for years, key in [(1, '1yr'), (3, '3yr'), (5, '5yr'), (10, '10yr')]:
        cutoff = now - timedelta(days=365 * years)
        result = (
            db.query(
                func.avg(SalesHistory.sale_price).label('avg'),
                func.count(SalesHistory.id).label('cnt'),
            )
            .filter(
                SalesHistory.postcode.like(f"{district}%"),
                SalesHistory.sale_date >= cutoff,
                SalesHistory.sale_price > 10000,
            )
            .first()
        )
        if result and result.avg:
            stats[f'avg_price_{key}'] = float(result.avg)
            stats[f'transaction_count_{key}'] = int(result.cnt)

    avg_1yr = stats.get('avg_price_1yr')
    avg_5yr = stats.get('avg_price_5yr')
    avg_10yr = stats.get('avg_price_10yr')

    if avg_1yr and avg_10yr:
        stats['growth_pct_10yr'] = (avg_1yr - avg_10yr) / avg_10yr
    if avg_1yr and avg_5yr:
        stats['growth_pct_5yr'] = (avg_1yr - avg_5yr) / avg_5yr

    # Yearly breakdown for chart
    yearly = (
        db.query(
            extract('year', SalesHistory.sale_date).label('year'),
            func.avg(SalesHistory.sale_price).label('avg_price'),
            func.count(SalesHistory.id).label('transactions'),
        )
        .filter(
            SalesHistory.postcode.like(f"{district}%"),
            SalesHistory.sale_date >= now - timedelta(days=365 * 10),
            SalesHistory.sale_price > 10000,
        )
        .group_by(extract('year', SalesHistory.sale_date))
        .order_by(extract('year', SalesHistory.sale_date))
        .all()
    )
    stats['sales_by_year'] = [
        {'year': int(r.year), 'avg_price': float(r.avg_price), 'transactions': int(r.transactions)}
        for r in yearly
    ]

    return stats


@router.get('/{postcode}/stats', response_model=AreaStats)
def get_area_stats(postcode: str, db: Session = Depends(get_db)):
    district = postcode.split(' ')[0].upper() if ' ' in postcode else postcode.upper()[:4]
    stats = _get_area_stats(db, district)
    if not stats.get('avg_price_1yr') and not stats.get('avg_price_10yr'):
        raise HTTPException(status_code=404, detail=f"No sales data found for area {district}")
    return AreaStats(**stats)


@router.get('/{postcode}/trends')
def get_area_trends(postcode: str, db: Session = Depends(get_db)):
    district = postcode.split(' ')[0].upper() if ' ' in postcode else postcode.upper()[:4]
    stats = _get_area_stats(db, district)
    return {
        'district': district,
        'sales_by_year': stats.get('sales_by_year', []),
        'growth_pct_10yr': stats.get('growth_pct_10yr'),
        'growth_pct_5yr': stats.get('growth_pct_5yr'),
        'avg_price_1yr': stats.get('avg_price_1yr'),
    }
