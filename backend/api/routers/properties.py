"""Property API endpoints."""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session, joinedload

from backend.api.dependencies import get_db, get_redis, PropertyFilters
from backend.api.schemas import (
    PropertyListResponse, PropertyDetail, PropertySummary,
    SalesHistoryItem, ReviewResponse,
)
from backend.models.property import Property, PropertyScore, PropertySource
from backend.models.property_ai_insight import PropertyAIInsight
from backend.models.sales_history import SalesHistory
from backend.models.auction import Auction

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/properties', tags=['properties'])

CACHE_TTL = 3600  # 1 hour


def _build_query(db: Session, filters: PropertyFilters):
    q = (
        db.query(Property)
        .outerjoin(PropertyScore, Property.id == PropertyScore.property_id)
        .options(joinedload(Property.score), joinedload(Property.ai_insight))
    )

    if filters.status:
        q = q.filter(Property.status == filters.status)
    if filters.postcode:
        q = q.filter(Property.postcode.ilike(f"{filters.postcode}%"))
    if filters.town:
        q = q.filter(Property.town.ilike(f"%{filters.town}%"))
    if filters.county:
        q = q.filter(Property.county.ilike(f"%{filters.county}%"))
    if filters.property_type:
        q = q.filter(Property.property_type == filters.property_type)
    if filters.min_beds is not None:
        q = q.filter(Property.bedrooms >= filters.min_beds)
    if filters.max_beds is not None:
        q = q.filter(Property.bedrooms <= filters.max_beds)
    if filters.min_price is not None:
        q = q.filter(Property.asking_price >= filters.min_price)
    if filters.max_price is not None:
        q = q.filter(Property.asking_price <= filters.max_price)
    if filters.is_reviewed is not None:
        q = q.filter(Property.is_reviewed == filters.is_reviewed)
    if filters.min_score is not None:
        q = q.filter(PropertyScore.investment_score >= filters.min_score)
    if filters.min_yield is not None:
        q = q.filter(PropertyScore.gross_yield_pct >= filters.min_yield)
    if filters.price_band:
        q = q.filter(PropertyScore.price_band == filters.price_band)

    # Sorting
    sort_col_map = {
        'investment_score': PropertyScore.investment_score,
        'asking_price': Property.asking_price,
        'date_found': Property.date_found,
        'yield': PropertyScore.gross_yield_pct,
        'price_deviation': PropertyScore.price_deviation_pct,
    }
    sort_col = sort_col_map.get(filters.sort_by, PropertyScore.investment_score)
    if filters.sort_dir == 'asc':
        q = q.order_by(asc(sort_col).nulls_last())
    else:
        q = q.order_by(desc(sort_col).nulls_last())

    return q


@router.get('', response_model=PropertyListResponse)
def list_properties(
    filters: PropertyFilters = Depends(),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis),
):
    cache_key = f"props:{hash(str(vars(filters)))}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    q = _build_query(db, filters)
    total = q.count()
    offset = (filters.page - 1) * filters.page_size
    items = q.offset(offset).limit(filters.page_size).all()

    result = PropertyListResponse(
        items=[PropertySummary.model_validate(p) for p in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=max(1, (total + filters.page_size - 1) // filters.page_size),
    )

    try:
        redis_client.setex(cache_key, CACHE_TTL, result.model_dump_json())
    except Exception:
        pass

    return result


@router.get('/high-value', response_model=PropertyListResponse)
def get_high_value_properties(
    min_score: float = 55.0,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """Properties with investment score >= threshold."""
    filters = PropertyFilters(min_score=min_score, sort_by='investment_score', sort_dir='desc',
                               page=page, page_size=page_size)
    q = _build_query(db, filters)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return PropertyListResponse(
        items=[PropertySummary.model_validate(p) for p in items],
        total=total, page=page, page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get('/{property_id}', response_model=PropertyDetail)
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = (
        db.query(Property)
        .options(
            joinedload(Property.score),
            joinedload(Property.sources),
            joinedload(Property.auctions),
            joinedload(Property.ai_insight),
        )
        .filter(Property.id == property_id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    detail = PropertyDetail.model_validate(prop)

    # Attach sales history
    history = (
        db.query(SalesHistory)
        .filter(
            SalesHistory.postcode == prop.postcode,
            SalesHistory.sale_price > 0,
        )
        .order_by(SalesHistory.sale_date.desc())
        .limit(50)
        .all()
    )
    detail.sales_history = [SalesHistoryItem.model_validate(h) for h in history]

    return detail


@router.get('/{property_id}/sales-history', response_model=list[SalesHistoryItem])
def get_sales_history(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    history = (
        db.query(SalesHistory)
        .filter(SalesHistory.postcode == prop.postcode)
        .order_by(SalesHistory.sale_date.asc())
        .limit(200)
        .all()
    )
    return [SalesHistoryItem.model_validate(h) for h in history]


@router.post('/{property_id}/review', response_model=ReviewResponse)
def mark_reviewed(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    prop.is_reviewed = not prop.is_reviewed
    prop.reviewed_at = datetime.utcnow() if prop.is_reviewed else None
    db.commit()
    db.refresh(prop)

    return ReviewResponse(
        property_id=prop.id,
        is_reviewed=prop.is_reviewed,
        reviewed_at=prop.reviewed_at,
        message="Marked as reviewed" if prop.is_reviewed else "Review removed",
    )
