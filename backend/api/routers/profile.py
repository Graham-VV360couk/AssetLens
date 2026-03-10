"""Property Attribute Profile endpoints."""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.models.property import Property
from backend.models.property_attribute_profile import PropertyAttributeProfile
from backend.services.attribute_estimator import PropertyAttributeEstimator

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/properties', tags=['profile'])


def _get_or_create_profile(
    property_id: int,
    db: Session,
    force_recalc: bool = False,
    overrides: Optional[dict] = None,
) -> PropertyAttributeProfile:
    """Load existing profile or create one. Returns the ORM object."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail='Property not found')

    existing = (
        db.query(PropertyAttributeProfile)
        .filter(PropertyAttributeProfile.property_id == property_id)
        .first()
    )

    # Load stored overrides (merge with any new ones passed in)
    stored_overrides = {}
    if existing and existing.override_payload:
        try:
            stored_overrides = json.loads(existing.override_payload)
        except Exception:
            pass

    merged_overrides = {**stored_overrides, **(overrides or {})}

    if existing and not force_recalc and not overrides:
        return existing

    # (Re)compute
    estimator = PropertyAttributeEstimator(db)
    result = estimator.estimate(prop, overrides=merged_overrides)

    computed_json = json.dumps(result['profile'])
    display_json = json.dumps(result['profile'])   # overrides already applied inside estimate()
    source_json = json.dumps(result['source_summary'])
    debug_json = json.dumps(result['debug'])
    override_json = json.dumps(merged_overrides)

    if existing:
        existing.computed_payload = computed_json
        existing.override_payload = override_json
        existing.display_payload = display_json
        existing.source_summary = source_json
        existing.debug_payload = debug_json
        existing.version += 1
        existing.generated_at = datetime.utcnow()
        existing.generated_by = 'system'
    else:
        existing = PropertyAttributeProfile(
            property_id=property_id,
            computed_payload=computed_json,
            override_payload=override_json,
            display_payload=display_json,
            source_summary=source_json,
            debug_payload=debug_json,
            version=1,
            generated_at=datetime.utcnow(),
            generated_by='system',
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def _profile_response(profile: PropertyAttributeProfile) -> dict:
    """Serialise a PropertyAttributeProfile ORM object to an API response dict."""
    try:
        display = json.loads(profile.display_payload or '{}')
    except Exception:
        display = {}
    try:
        source_summary = json.loads(profile.source_summary or '{}')
    except Exception:
        source_summary = {}
    try:
        overrides = json.loads(profile.override_payload or '{}')
    except Exception:
        overrides = {}

    return {
        'property_id': profile.property_id,
        'profile': display,
        'source_summary': source_summary,
        'overrides': overrides,
        'version': profile.version,
        'generated_at': profile.generated_at.isoformat() if profile.generated_at else None,
    }


# ---------------------------------------------------------------------------
# GET  /api/properties/{id}/profile
# ---------------------------------------------------------------------------

@router.get('/{property_id}/profile')
def get_property_profile(property_id: int, db: Session = Depends(get_db)):
    """
    Return the computed property attribute profile for a property.

    Creates the profile on first call; returns cached version on subsequent calls.
    To force a full recompute, use POST /recalculate.
    """
    profile = _get_or_create_profile(property_id, db)
    return _profile_response(profile)


# ---------------------------------------------------------------------------
# POST /api/properties/{id}/profile/recalculate
# ---------------------------------------------------------------------------

@router.post('/{property_id}/profile/recalculate')
def recalculate_profile(property_id: int, db: Session = Depends(get_db)):
    """Force a full recomputation of the property attribute profile."""
    profile = _get_or_create_profile(property_id, db, force_recalc=True)
    return _profile_response(profile)


# ---------------------------------------------------------------------------
# POST /api/properties/{id}/profile/override
# ---------------------------------------------------------------------------

class OverridePayload(BaseModel):
    field: str
    value: object
    note: Optional[str] = None


OVERRIDEABLE_FIELDS = {
    'property_type', 'bedrooms', 'bathrooms',
    'reception_rooms', 'floor_area_sqm', 'plot_size_sqm',
}


@router.post('/{property_id}/profile/override')
def override_attribute(
    property_id: int,
    body: OverridePayload,
    db: Session = Depends(get_db),
):
    """
    Apply a user override for a single attribute field and trigger a
    full re-evaluation of the property profile using the new value as
    a trusted input.

    Overrides are persisted and included in all subsequent recalculations.
    """
    if body.field not in OVERRIDEABLE_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=f"Field '{body.field}' is not overrideable. "
                   f"Allowed fields: {sorted(OVERRIDEABLE_FIELDS)}",
        )

    # Load existing overrides and add the new one
    existing = (
        db.query(PropertyAttributeProfile)
        .filter(PropertyAttributeProfile.property_id == property_id)
        .first()
    )
    current_overrides: dict = {}
    if existing and existing.override_payload:
        try:
            current_overrides = json.loads(existing.override_payload)
        except Exception:
            pass

    current_overrides[body.field] = body.value

    # Recompute with all overrides
    profile = _get_or_create_profile(
        property_id, db,
        force_recalc=True,
        overrides=current_overrides,
    )

    response = _profile_response(profile)
    response['recalculated_using_override'] = True
    response['override_applied'] = {'field': body.field, 'value': body.value}
    return response


# ---------------------------------------------------------------------------
# DELETE /api/properties/{id}/profile/override/{field}
# ---------------------------------------------------------------------------

@router.delete('/{property_id}/profile/override/{field_name}')
def remove_override(property_id: int, field_name: str, db: Session = Depends(get_db)):
    """Remove a specific user override and recompute the profile."""
    existing = (
        db.query(PropertyAttributeProfile)
        .filter(PropertyAttributeProfile.property_id == property_id)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail='No profile found for this property')

    current_overrides: dict = {}
    if existing.override_payload:
        try:
            current_overrides = json.loads(existing.override_payload)
        except Exception:
            pass

    current_overrides.pop(field_name, None)

    profile = _get_or_create_profile(
        property_id, db,
        force_recalc=True,
        overrides=current_overrides,
    )
    return _profile_response(profile)


# ---------------------------------------------------------------------------
# GET  /api/properties/{id}/profile/debug
# ---------------------------------------------------------------------------

@router.get('/{property_id}/profile/debug')
def get_profile_debug(property_id: int, db: Session = Depends(get_db)):
    """
    Return the raw debug payload for a property profile (admin/developer view).
    Includes: input facts, warnings, contradictions found, source decisions.
    """
    existing = (
        db.query(PropertyAttributeProfile)
        .filter(PropertyAttributeProfile.property_id == property_id)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail='No profile found — call GET /profile first')

    try:
        debug = json.loads(existing.debug_payload or '{}')
    except Exception:
        debug = {}
    try:
        computed = json.loads(existing.computed_payload or '{}')
    except Exception:
        computed = {}

    return {
        'property_id': property_id,
        'version': existing.version,
        'generated_at': existing.generated_at.isoformat() if existing.generated_at else None,
        'debug': debug,
        'computed_profile': computed,
    }
