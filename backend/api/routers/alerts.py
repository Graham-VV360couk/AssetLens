"""Alert preferences and matched properties API."""
import json
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import get_current_user
from backend.models.user import User
from backend.models.alert_preference import UserAlertPreference
from backend.models.property import Property

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/alerts', tags=['alerts'])


class AlertPreferencesSchema(BaseModel):
    is_active: Optional[bool] = None
    min_match_pct: Optional[int] = None
    alert_frequency: Optional[str] = None  # immediate, daily, weekly
    location_filter: Optional[str] = None
    max_price: Optional[int] = None
    min_beds: Optional[int] = None
    property_types: Optional[str] = None


class AlertPreferencesResponse(BaseModel):
    is_active: bool = True
    min_match_pct: int = 60
    alert_frequency: str = 'daily'
    location_filter: Optional[str] = None
    max_price: Optional[int] = None
    min_beds: Optional[int] = None
    property_types: Optional[str] = None
    last_alerted_at: Optional[datetime] = None


class MatchedPropertySchema(BaseModel):
    id: int
    address: Optional[str]
    postcode: Optional[str]
    asking_price: Optional[float]
    property_type: Optional[str]
    bedrooms: Optional[int]
    image_url: Optional[str]
    match_pct: int
    match_reasons: List[str] = []


@router.get('/preferences', response_model=AlertPreferencesResponse)
def get_alert_preferences(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the current user's alert preferences."""
    pref = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user.id
    ).first()

    if not pref:
        return AlertPreferencesResponse()

    return AlertPreferencesResponse(
        is_active=pref.is_active,
        min_match_pct=pref.min_match_pct,
        alert_frequency=pref.alert_frequency,
        location_filter=pref.location_filter,
        max_price=pref.max_price,
        min_beds=pref.min_beds,
        property_types=pref.property_types,
        last_alerted_at=pref.last_alerted_at,
    )


@router.put('/preferences', response_model=AlertPreferencesResponse)
def update_alert_preferences(
    data: AlertPreferencesSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update the current user's alert preferences."""
    pref = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user.id
    ).first()

    if not pref:
        pref = UserAlertPreference(user_id=user.id)
        db.add(pref)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pref, field, value)

    pref.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pref)

    return AlertPreferencesResponse(
        is_active=pref.is_active,
        min_match_pct=pref.min_match_pct,
        alert_frequency=pref.alert_frequency,
        location_filter=pref.location_filter,
        max_price=pref.max_price,
        min_beds=pref.min_beds,
        property_types=pref.property_types,
        last_alerted_at=pref.last_alerted_at,
    )


@router.get('/matches', response_model=List[MatchedPropertySchema])
def get_matched_properties(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 30,
):
    """Get properties that match the user's scoring preferences above their threshold."""
    from backend.services.alert_matcher import get_matches_for_user
    return get_matches_for_user(db, user, limit=limit)
