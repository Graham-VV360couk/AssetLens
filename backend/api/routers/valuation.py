"""User property portfolio and valuation API."""
import json
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import get_current_user
from backend.models.user import User
from backend.models.user_property import UserProperty, PropertyValuation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/valuation", tags=["valuation"])


# ============================================================================
# Schemas
# ============================================================================

class UserPropertyCreate(BaseModel):
    address_line1: str
    address_line2: Optional[str] = None
    town: str
    postcode: str
    property_type: str
    bedrooms: int
    bathrooms: Optional[int] = None
    relationship_to_property: str
    tenure: str
    lease_years_remaining: Optional[int] = None


class UserPropertyResponse(BaseModel):
    id: int
    address_line1: str
    address_line2: Optional[str] = None
    town: str
    postcode: str
    property_type: str
    bedrooms: int
    bathrooms: Optional[int] = None
    relationship_to_property: str
    tenure: str
    lease_years_remaining: Optional[int] = None
    latest_valuation: Optional[dict] = None


class ValuationRequest(BaseModel):
    """All answers from the 5-section wizard."""
    basics: Optional[dict] = {}
    features: Optional[dict] = {}
    condition: Optional[dict] = {}
    situation: Optional[dict] = {}
    supporting: Optional[dict] = {}


class ValuationResponse(BaseModel):
    id: int
    avm_baseline: Optional[float] = None
    avm_source: Optional[str] = None
    feature_adjustment: Optional[float] = None
    feature_breakdown: Optional[list] = None
    condition_adjustment: Optional[float] = None
    condition_breakdown: Optional[list] = None
    situation_band: Optional[str] = None
    range_low: Optional[float] = None
    range_mid: Optional[float] = None
    range_high: Optional[float] = None
    created_at: Optional[datetime] = None


# ============================================================================
# Portfolio endpoints
# ============================================================================

@router.get("/properties", response_model=List[UserPropertyResponse])
def list_my_properties(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all properties in the user's portfolio."""
    props = db.query(UserProperty).filter(
        UserProperty.user_id == user.id
    ).order_by(UserProperty.created_at.desc()).all()

    result = []
    for p in props:
        latest = (
            db.query(PropertyValuation)
            .filter(PropertyValuation.user_property_id == p.id)
            .order_by(PropertyValuation.created_at.desc())
            .first()
        )
        resp = UserPropertyResponse(
            id=p.id,
            address_line1=p.address_line1,
            address_line2=p.address_line2,
            town=p.town,
            postcode=p.postcode,
            property_type=p.property_type,
            bedrooms=p.bedrooms,
            bathrooms=p.bathrooms,
            relationship_to_property=p.relationship_to_property,
            tenure=p.tenure,
            lease_years_remaining=p.lease_years_remaining,
        )
        if latest:
            resp.latest_valuation = {
                'range_low': latest.range_low,
                'range_mid': latest.range_mid,
                'range_high': latest.range_high,
                'created_at': latest.created_at.isoformat() if latest.created_at else None,
            }
        result.append(resp)

    return result


@router.post("/properties", status_code=201, response_model=UserPropertyResponse)
def add_property(
    data: UserPropertyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a property to the user's portfolio."""
    prop = UserProperty(
        user_id=user.id,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        town=data.town,
        postcode=data.postcode.upper().strip(),
        property_type=data.property_type,
        bedrooms=data.bedrooms,
        bathrooms=data.bathrooms,
        relationship_to_property=data.relationship_to_property,
        tenure=data.tenure,
        lease_years_remaining=data.lease_years_remaining,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)

    return UserPropertyResponse(
        id=prop.id,
        address_line1=prop.address_line1,
        address_line2=prop.address_line2,
        town=prop.town,
        postcode=prop.postcode,
        property_type=prop.property_type,
        bedrooms=prop.bedrooms,
        bathrooms=prop.bathrooms,
        relationship_to_property=prop.relationship_to_property,
        tenure=prop.tenure,
        lease_years_remaining=prop.lease_years_remaining,
    )


@router.put("/properties/{property_id}", response_model=UserPropertyResponse)
def update_property(
    property_id: int,
    data: UserPropertyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a property in the user's portfolio."""
    prop = db.query(UserProperty).filter(
        UserProperty.id == property_id,
        UserProperty.user_id == user.id,
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail='Property not found')

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == 'postcode':
            value = value.upper().strip()
        setattr(prop, field, value)

    prop.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prop)

    return UserPropertyResponse(
        id=prop.id,
        address_line1=prop.address_line1,
        address_line2=prop.address_line2,
        town=prop.town,
        postcode=prop.postcode,
        property_type=prop.property_type,
        bedrooms=prop.bedrooms,
        bathrooms=prop.bathrooms,
        relationship_to_property=prop.relationship_to_property,
        tenure=prop.tenure,
        lease_years_remaining=prop.lease_years_remaining,
    )


@router.delete("/properties/{property_id}")
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove a property from the user's portfolio."""
    prop = db.query(UserProperty).filter(
        UserProperty.id == property_id,
        UserProperty.user_id == user.id,
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail='Property not found')

    db.delete(prop)
    db.commit()
    return {'deleted': True}


# ============================================================================
# Valuation endpoints
# ============================================================================

@router.post("/properties/{property_id}/value", response_model=ValuationResponse)
def calculate_value(
    property_id: int,
    answers: ValuationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run the valuation calculation for a property. Creates a new versioned result."""
    prop = db.query(UserProperty).filter(
        UserProperty.id == property_id,
        UserProperty.user_id == user.id,
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail='Property not found')

    from backend.services.valuation_engine import calculate_valuation, save_valuation

    answers_dict = answers.model_dump()
    result = calculate_valuation(db, prop, answers_dict)

    if 'error' in result:
        raise HTTPException(status_code=422, detail=result['error'])

    valuation = save_valuation(db, prop.id, user.id, answers_dict, result)

    return ValuationResponse(
        id=valuation.id,
        avm_baseline=result.get('avm_baseline'),
        avm_source=result.get('avm_source'),
        feature_adjustment=result.get('feature_adjustment'),
        feature_breakdown=result.get('feature_breakdown'),
        condition_adjustment=result.get('condition_adjustment'),
        condition_breakdown=result.get('condition_breakdown'),
        situation_band=result.get('situation_band'),
        range_low=result.get('range_low'),
        range_mid=result.get('range_mid'),
        range_high=result.get('range_high'),
        created_at=valuation.created_at,
    )


@router.get("/properties/{property_id}/history", response_model=List[ValuationResponse])
def get_valuation_history(
    property_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all valuation results for a property (versioned history)."""
    prop = db.query(UserProperty).filter(
        UserProperty.id == property_id,
        UserProperty.user_id == user.id,
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail='Property not found')

    valuations = (
        db.query(PropertyValuation)
        .filter(PropertyValuation.user_property_id == prop.id)
        .order_by(PropertyValuation.created_at.desc())
        .all()
    )

    return [
        ValuationResponse(
            id=v.id,
            avm_baseline=v.avm_baseline,
            avm_source=v.avm_source,
            feature_adjustment=v.feature_adjustment,
            condition_adjustment=v.condition_adjustment,
            situation_band=v.situation_band,
            range_low=v.range_low,
            range_mid=v.range_mid,
            range_high=v.range_high,
            created_at=v.created_at,
        )
        for v in valuations
    ]
