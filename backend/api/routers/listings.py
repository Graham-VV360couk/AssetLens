"""Public listing pages — no auth required. Field visibility rules applied."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import get_optional_user
from backend.models.property import Property, PropertyScore
from backend.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/listings", tags=["listings"])


def _get_listing_property(db: Session, property_id: int) -> Property:
    prop = db.query(Property).get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Listing not found")
    return prop


def _public_view(prop) -> dict:
    """Strip gated fields for unauthenticated/public access."""
    photos = []
    if prop.image_urls:
        try:
            all_photos = json.loads(prop.image_urls)
            photos = all_photos[:3]
        except (json.JSONDecodeError, TypeError):
            pass

    postcode = getattr(prop, 'postcode', '') or ''
    district = postcode.split()[0] if ' ' in postcode else postcode[:4]

    return {
        'id': prop.id,
        'address': getattr(prop, 'town', None) or 'Unknown area',
        'postcode': district,
        'asking_price': prop.asking_price,
        'property_type': prop.property_type,
        'bedrooms': prop.bedrooms,
        'bathrooms': prop.bathrooms,
        'description': prop.description,
        'photos': photos,
        'ai_score': None,
        'avm': None,
        'yield_pct': None,
    }


def _investor_view(prop, db: Session) -> dict:
    """Full data for authenticated investor."""
    photos = []
    if prop.image_urls:
        try:
            photos = json.loads(prop.image_urls)
        except (json.JSONDecodeError, TypeError):
            pass

    score = db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()

    return {
        'id': prop.id,
        'address': prop.address,
        'postcode': prop.postcode,
        'asking_price': prop.asking_price,
        'property_type': prop.property_type,
        'bedrooms': prop.bedrooms,
        'bathrooms': prop.bathrooms,
        'description': prop.description,
        'photos': photos,
        'ai_score': score.investment_score if score else None,
        'avm': score.pd_avm if score else None,
        'yield_pct': score.gross_yield_pct if score else None,
        'epc_rating': prop.epc_energy_rating,
        'flood_risk': score.pd_flood_risk if score else None,
    }


@router.get("/{property_id}")
def get_public_listing(
    property_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    prop = _get_listing_property(db, property_id)
    if user and user.subscription_status in ('active', 'past_due') and user.subscription_tier in ('investor', 'admin'):
        return _investor_view(prop, db)
    return _public_view(prop)


def _get_uploader_listings(db: Session, uploader: User, source_name: str, viewer: Optional[User]):
    """Get public listing view for an uploader's properties."""
    from backend.models.property import PropertySource
    props = (
        db.query(Property)
        .join(PropertySource, Property.id == PropertySource.property_id)
        .filter(
            PropertySource.source_name == source_name,
            PropertySource.source_id.like(f'{uploader.id}_%'),
            PropertySource.is_active == True,
            Property.status == 'active',
        )
        .order_by(Property.date_found.desc())
        .limit(100)
        .all()
    )

    is_investor = (viewer and viewer.subscription_status in ('active', 'past_due')
                   and viewer.subscription_tier in ('investor', 'admin'))

    profile = uploader.profile if hasattr(uploader, 'profile') and uploader.profile else None
    brand = {}
    if profile:
        brand = {
            'logo_url': profile.brand_logo_url,
            'primary_colour': profile.brand_primary_colour,
            'accent_colour': profile.brand_accent_colour,
            'company_name': uploader.company_name or uploader.full_name,
        }

    listings = []
    for prop in props:
        if is_investor:
            listings.append(_investor_view(prop, db))
        else:
            listings.append(_public_view(prop))

    return {
        'uploader': uploader.full_name,
        'company': uploader.company_name,
        'brand': brand,
        'total': len(listings),
        'listings': listings,
    }


@router.get("/auction/{username}")
def get_auction_listings(
    username: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """List all active properties uploaded by an auction house."""
    uploader = db.query(User).filter(User.email == username).first()
    if not uploader:
        raise HTTPException(status_code=404, detail="Auction house not found")
    return _get_uploader_listings(db, uploader, 'auction_upload', user)


@router.get("/deal/{username}")
def get_deal_listings(
    username: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """List all active properties uploaded by a deal source."""
    uploader = db.query(User).filter(User.email == username).first()
    if not uploader:
        raise HTTPException(status_code=404, detail="Deal source not found")
    return _get_uploader_listings(db, uploader, 'deal_upload', user)


@router.get("/agent/{username}")
def get_agent_listings(
    username: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """List all active properties uploaded by an estate agent. Branded page."""
    uploader = db.query(User).filter(User.email == username).first()
    if not uploader:
        raise HTTPException(status_code=404, detail="Estate agent not found")
    return _get_uploader_listings(db, uploader, 'agent_upload', user)
