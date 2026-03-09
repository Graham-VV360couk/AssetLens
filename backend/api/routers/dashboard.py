"""Dashboard statistics endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.api.dependencies import get_db
from backend.api.schemas import DashboardStats, PropertySummary
from backend.models.property import Property, PropertyScore

router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])


@router.get('/stats', response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_active = db.query(func.count(Property.id)).filter(Property.status == 'active').scalar() or 0
    total_reviewed = db.query(func.count(Property.id)).filter(
        Property.status == 'active', Property.is_reviewed == True
    ).scalar() or 0
    high_value = db.query(func.count(PropertyScore.id)).filter(
        PropertyScore.investment_score >= 55
    ).scalar() or 0

    agg = db.query(
        func.avg(PropertyScore.investment_score).label('avg_score'),
        func.avg(PropertyScore.gross_yield_pct).label('avg_yield'),
    ).first()

    # By price band
    band_rows = (
        db.query(PropertyScore.price_band, func.count(PropertyScore.id))
        .group_by(PropertyScore.price_band)
        .all()
    )
    by_price_band = {r[0] or 'unknown': r[1] for r in band_rows}

    # By property type
    type_rows = (
        db.query(Property.property_type, func.count(Property.id))
        .filter(Property.status == 'active')
        .group_by(Property.property_type)
        .all()
    )
    by_property_type = {r[0] or 'unknown': r[1] for r in type_rows}

    # Recent high value properties
    recent_hv = (
        db.query(Property)
        .join(PropertyScore, Property.id == PropertyScore.property_id)
        .options(joinedload(Property.score))
        .filter(PropertyScore.investment_score >= 55)
        .order_by(PropertyScore.investment_score.desc())
        .limit(6)
        .all()
    )

    return DashboardStats(
        total_active=total_active,
        total_reviewed=total_reviewed,
        high_value_count=high_value,
        avg_investment_score=float(agg.avg_score) if agg and agg.avg_score else None,
        avg_yield=float(agg.avg_yield) if agg and agg.avg_yield else None,
        by_price_band=by_price_band,
        by_property_type=by_property_type,
        recent_high_value=[PropertySummary.model_validate(p) for p in recent_hv],
    )
