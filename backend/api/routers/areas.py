"""Area statistics API endpoints."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, extract, and_
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


@router.get('/national/trends')
def get_national_trends(db: Session = Depends(get_db)):
    """National (England & Wales) average price per year — for comparison overlay."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=365 * 10)
    rows = (
        db.query(
            extract('year', SalesHistory.sale_date).label('year'),
            func.avg(SalesHistory.sale_price).label('avg_price'),
            func.count(SalesHistory.id).label('transactions'),
        )
        .filter(
            SalesHistory.sale_date >= cutoff,
            SalesHistory.sale_price > 10000,
            SalesHistory.sale_price < 5_000_000,
        )
        .group_by(extract('year', SalesHistory.sale_date))
        .order_by(extract('year', SalesHistory.sale_date))
        .all()
    )
    return [
        {'year': int(r.year), 'avg_price': round(float(r.avg_price)), 'transactions': int(r.transactions)}
        for r in rows
    ]


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


# Map property-listing types to Land Registry codes
_TYPE_TO_LR = {
    'detached': 'D',
    'semi-detached': 'S', 'semi_detached': 'S', 'semi detached': 'S',
    'terraced': 'T', 'end of terrace': 'T', 'mid terrace': 'T',
    'flat': 'F', 'apartment': 'F', 'maisonette': 'F',
}


@router.get('/{postcode}/comparables')
def get_comparables(
    postcode: str,
    property_type: Optional[str] = Query(None),
    limit: int = Query(12, le=30),
    db: Session = Depends(get_db),
):
    """Recent comparable sales in same postcode district."""
    district = postcode.split(' ')[0].upper() if ' ' in postcode else postcode.upper()[:4]
    cutoff = datetime.utcnow() - timedelta(days=365 * 3)

    lr_type = _TYPE_TO_LR.get((property_type or '').lower())

    q = (
        db.query(SalesHistory)
        .filter(
            SalesHistory.postcode.like(f'{district}%'),
            SalesHistory.sale_date >= cutoff,
            SalesHistory.sale_price > 10000,
        )
    )
    if lr_type:
        q = q.filter(SalesHistory.property_type == lr_type)

    rows = q.order_by(SalesHistory.sale_date.desc()).limit(limit).all()

    _LR_LABEL = {'D': 'Detached', 'S': 'Semi-det.', 'T': 'Terraced', 'F': 'Flat', 'O': 'Other'}
    return [
        {
            'address': r.address,
            'postcode': r.postcode,
            'sale_date': r.sale_date.isoformat() if r.sale_date else None,
            'sale_price': int(r.sale_price),
            'property_type': _LR_LABEL.get(r.property_type, r.property_type),
            'new_build': r.old_new == 'Y',
        }
        for r in rows
    ]


@router.get('/{postcode}/price-distribution')
def get_price_distribution(
    postcode: str,
    guide_price: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Histogram of sale prices in district (last 3 years). guide_price marks position."""
    district = postcode.split(' ')[0].upper() if ' ' in postcode else postcode.upper()[:4]
    cutoff = datetime.utcnow() - timedelta(days=365 * 3)

    rows = (
        db.query(SalesHistory.sale_price)
        .filter(
            SalesHistory.postcode.like(f'{district}%'),
            SalesHistory.sale_date >= cutoff,
            SalesHistory.sale_price > 10000,
            SalesHistory.sale_price < 5_000_000,
        )
        .all()
    )

    if not rows:
        return {'buckets': [], 'guide_price': guide_price, 'total': 0}

    prices = [r[0] for r in rows]
    lo, hi = min(prices), max(prices)

    # 20 buckets; snap to clean £25K boundaries
    step = max(25_000, round((hi - lo) / 20 / 25_000) * 25_000)
    lo_snap = (int(lo) // step) * step
    hi_snap = (int(hi) // step + 1) * step

    buckets = []
    b = lo_snap
    while b < hi_snap:
        top = b + step
        count = sum(1 for p in prices if b <= p < top)
        buckets.append({'from': b, 'to': top, 'label': f'£{b//1000}K', 'count': count})
        b = top

    percentile = None
    if guide_price:
        below = sum(1 for p in prices if p < guide_price)
        percentile = round(below / len(prices) * 100)

    return {
        'buckets': buckets,
        'guide_price': guide_price,
        'percentile': percentile,
        'total': len(prices),
        'median': sorted(prices)[len(prices) // 2],
        'avg': round(sum(prices) / len(prices)),
    }
