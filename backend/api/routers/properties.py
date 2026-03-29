"""Property API endpoints."""
import json
import logging
from datetime import datetime
from math import cos, radians
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

    if filters.source:
        q = q.join(PropertySource, Property.id == PropertySource.property_id).filter(
            PropertySource.source_name == filters.source
        )

    if filters.status:
        statuses = [s.strip() for s in filters.status.split(',') if s.strip()]
        if len(statuses) == 1:
            q = q.filter(Property.status == statuses[0])
        else:
            q = q.filter(Property.status.in_(statuses))

    # Radius search takes precedence over postcode chip filter
    if filters.center_postcode and filters.radius_miles:
        from backend.services.geocoder import geocode_postcode
        coords = geocode_postcode(filters.center_postcode)
        if coords:
            clat, clon = coords
            lat_d = filters.radius_miles / 69.0
            lon_d = filters.radius_miles / (69.0 * cos(radians(clat)))
            # Bounding-box pre-filter (uses index on lat/lon)
            q = q.filter(
                Property.latitude.isnot(None),
                Property.latitude.between(clat - lat_d, clat + lat_d),
                Property.longitude.between(clon - lon_d, clon + lon_d),
            )
            # Exact haversine distance filter
            dist_expr = (3959 * func.acos(
                func.least(1.0,
                    func.cos(func.radians(clat)) *
                    func.cos(func.radians(Property.latitude)) *
                    func.cos(func.radians(Property.longitude) - func.radians(clon)) +
                    func.sin(func.radians(clat)) *
                    func.sin(func.radians(Property.latitude))
                )
            ))
            q = q.filter(dist_expr <= filters.radius_miles)
    elif filters.postcode:
        districts = [p.strip().upper() for p in filters.postcode.split(',') if p.strip()]
        if len(districts) == 1:
            q = q.filter(Property.postcode.ilike(f"{districts[0]}%"))
        else:
            from sqlalchemy import or_ as _or_
            q = q.filter(_or_(*[Property.postcode.ilike(f"{d}%") for d in districts]))

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


def _compute_distance_miles(clat: float, clon: float, lat: Optional[float], lon: Optional[float]) -> Optional[float]:
    """Haversine distance in miles between center and a property coordinate."""
    if lat is None or lon is None:
        return None
    import math
    R = 3959.0
    dlat = math.radians(lat - clat)
    dlon = math.radians(lon - clon)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(clat)) * math.cos(math.radians(lat)) *
         math.sin(dlon / 2) ** 2)
    return round(R * 2 * math.asin(math.sqrt(a)), 2)


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

    # Compute distance_miles when radius filter is active
    center_coords = None
    if filters.center_postcode and filters.radius_miles:
        from backend.services.geocoder import geocode_postcode
        center_coords = geocode_postcode(filters.center_postcode)

    summaries = []
    for p in items:
        s = PropertySummary.model_validate(p)
        if center_coords:
            s.distance_miles = _compute_distance_miles(
                center_coords[0], center_coords[1], p.latitude, p.longitude
            )
        summaries.append(s)

    result = PropertyListResponse(
        items=summaries,
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


import re as _re
_POSTCODE_RE = _re.compile(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}$', _re.IGNORECASE)


@router.post('/{property_id}/postcode')
def set_postcode(property_id: int, body: dict, db: Session = Depends(get_db)):
    """Save a manually-entered postcode and immediately re-score the property."""
    postcode = (body.get('postcode') or '').strip().upper()
    if not postcode or not _POSTCODE_RE.match(postcode):
        raise HTTPException(status_code=422, detail='Invalid UK postcode format')

    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail='Property not found')

    prop.postcode = postcode
    db.commit()

    # Re-score immediately so area stats, valuation and yield use the new postcode
    from backend.services.scoring_service import PropertyScoringService, save_score
    from backend.models.property import PropertyScore
    existing_score = db.query(PropertyScore).filter(PropertyScore.property_id == property_id).first()
    scorer = PropertyScoringService(db)
    result = scorer.score_property(prop, existing_score=existing_score)
    save_score(db, prop.id, result, existing_score=existing_score)
    db.refresh(prop)

    return {'property_id': prop.id, 'postcode': postcode, 'message': 'Postcode saved and property re-scored'}


@router.post('/fix-postcodes')
def fix_missing_postcodes(
    limit: int = 20,
    background_tasks=None,
    db: Session = Depends(get_db),
):
    """Use Claude Haiku to infer postcodes for properties where postcode is blank."""
    from backend.services.ai_analysis_service import ai_guess_postcode

    props = (
        db.query(Property)
        .filter(
            (Property.postcode == None) | (Property.postcode == ''),
            Property.status == 'active',
        )
        .limit(limit)
        .all()
    )

    fixed = []
    failed = []
    for prop in props:
        guessed = ai_guess_postcode(prop.address)
        if guessed:
            prop.postcode = guessed
            db.commit()
            fixed.append({'id': prop.id, 'address': prop.address[:80], 'postcode': guessed})
        else:
            failed.append(prop.id)

    return {
        'message': f'Fixed {len(fixed)} postcodes, {len(failed)} unresolved',
        'fixed': fixed,
        'unresolved_ids': failed,
    }


@router.post('/fetch-images')
def fetch_images_for_existing(limit: int = 30, db: Session = Depends(get_db)):
    """Backfill image_url for properties that have a source_url but no image."""
    import time, requests as _req
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    props = (
        db.query(Property)
        .join(Property.sources)
        .filter(
            (Property.image_url == None) | (Property.image_url == ''),
            Property.status == 'active',
            PropertySource.source_url != None,
            PropertySource.source_url != '',
        )
        .limit(limit)
        .all()
    )

    headers = {'User-Agent': 'Mozilla/5.0 (compatible; AssetLens/1.0)'}
    updated = []
    failed = []

    for prop in props:
        source_url = next((s.source_url for s in prop.sources if s.source_url), None)
        if not source_url:
            continue
        try:
            time.sleep(1.5)
            r = _req.get(source_url, headers=headers, timeout=20)
            if not r.ok:
                failed.append(prop.id)
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            selectors = [
                'img.property-image', 'img.lot-image', 'img[class*="property"]',
                '.gallery img', '.carousel img:first-child',
                'img[src*="property"]', 'img[src*="lot"]',
                'img[data-src]', 'img[src]',
            ]
            img_url = None
            for sel in selectors:
                el = soup.select_one(sel)
                if el:
                    src = el.get('src') or el.get('data-src') or ''
                    if src and not src.startswith('data:') and len(src) > 10:
                        img_url = urljoin(source_url, src)
                        break
            if img_url:
                prop.image_url = img_url
                db.commit()
                updated.append({'id': prop.id, 'image_url': img_url})
            else:
                failed.append(prop.id)
        except Exception as e:
            logger.warning("fetch_images: property %d failed: %s", prop.id, e)
            failed.append(prop.id)

    return {
        'message': f'Updated {len(updated)} images, {len(failed)} failed',
        'updated': updated,
        'failed_ids': failed,
    }
