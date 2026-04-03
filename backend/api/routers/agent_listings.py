"""Estate agent property upload portal.

Estate agents can upload properties via single form or CSV bulk.
Each upload triggers:
1. Deduplication check
2. Property creation with source tracking
3. Neighbourhood enrichment (async)
4. Alert matching against all users with active alerts
"""
import csv
import io
import json
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import get_current_user, check_subscription
from backend.models.property import Property, PropertySource
from backend.models.user import User
from backend.services.deduplication_service import PropertyDeduplicator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent-listings", tags=["agent-listings"])


class AgentListingCreate(BaseModel):
    address: str
    postcode: str
    asking_price: Optional[float] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    reception_rooms: Optional[int] = None
    description: Optional[str] = None
    epc_rating: Optional[str] = None
    tenure: Optional[str] = None         # freehold, leasehold
    status: Optional[str] = 'active'     # available, under_offer, sold_stc


class AgentListingResponse(BaseModel):
    id: int
    address: str
    postcode: str
    asking_price: Optional[float] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    status: Optional[str] = None
    deduplicated: bool = False


def _trigger_post_upload(prop_id: int):
    """Queue enrichment and alert matching after a property is uploaded."""
    # Enrichment
    try:
        from backend.tasks.enrichment import enrich_property_task
        enrich_property_task.delay(prop_id)
    except Exception as e:
        logger.debug("Celery enrichment not available, will enrich on next batch: %s", e)

    # Direct enrichment fallback (if Celery not running)
    try:
        from backend.models.base import SessionLocal
        from backend.models.property import Property as PropModel
        from backend.services.neighbourhood_service import enrich_property
        db = SessionLocal()
        prop = db.query(PropModel).get(prop_id)
        if prop and not prop.neighbourhood_enriched_at:
            enrich_property(db, prop)
            db.commit()
        db.close()
    except Exception as e:
        logger.debug("Direct enrichment skipped: %s", e)


@router.post("", status_code=201, response_model=AgentListingResponse)
def create_agent_listing(
    listing: AgentListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a single property listing as an estate agent."""
    check_subscription(user, ['estate_agent', 'white_label', 'admin'])

    dedup = PropertyDeduplicator(db)
    existing = dedup.find_duplicate(address=listing.address, postcode=listing.postcode)
    if existing:
        return AgentListingResponse(
            id=existing.id, address=existing.address, postcode=existing.postcode,
            asking_price=existing.asking_price, deduplicated=True,
        )

    prop = Property(
        address=listing.address,
        postcode=listing.postcode.upper().strip(),
        property_type=listing.property_type or 'other',
        bedrooms=listing.bedrooms,
        bathrooms=listing.bathrooms,
        reception_rooms=listing.reception_rooms,
        asking_price=listing.asking_price,
        description=listing.description,
        epc_energy_rating=listing.epc_rating,
        status='active',
        date_found=datetime.utcnow(),
    )
    db.add(prop)
    db.flush()

    source = PropertySource(
        property_id=prop.id,
        source_name='agent_upload',
        source_id=f'{user.id}_{prop.id}',
        is_active=True,
    )
    db.add(source)
    db.commit()

    _trigger_post_upload(prop.id)

    return AgentListingResponse(
        id=prop.id, address=prop.address, postcode=prop.postcode,
        asking_price=prop.asking_price, property_type=prop.property_type,
        bedrooms=prop.bedrooms, status=prop.status, deduplicated=False,
    )


@router.post("/upload-csv")
async def upload_agent_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Bulk upload properties from CSV.

    Expected columns: address, postcode, asking_price, property_type,
    bedrooms, bathrooms, reception_rooms, description, epc_rating, tenure
    """
    check_subscription(user, ['estate_agent', 'white_label', 'admin'])

    content = await file.read()
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))

    stats = {'imported': 0, 'duplicates': 0, 'errors': 0}
    dedup = PropertyDeduplicator(db)
    new_ids = []

    for row in reader:
        try:
            address = row.get('address', '').strip()
            postcode = row.get('postcode', '').strip().upper()
            if not postcode or not address:
                stats['errors'] += 1
                continue

            existing = dedup.find_duplicate(address=address, postcode=postcode)
            if existing:
                stats['duplicates'] += 1
                continue

            prop = Property(
                address=address,
                postcode=postcode,
                property_type=row.get('property_type', 'other'),
                bedrooms=int(row['bedrooms']) if row.get('bedrooms') else None,
                bathrooms=int(row['bathrooms']) if row.get('bathrooms') else None,
                reception_rooms=int(row['reception_rooms']) if row.get('reception_rooms') else None,
                asking_price=float(row['asking_price']) if row.get('asking_price') else None,
                description=row.get('description'),
                epc_energy_rating=row.get('epc_rating'),
                status='active',
                date_found=datetime.utcnow(),
            )
            db.add(prop)
            db.flush()

            source = PropertySource(
                property_id=prop.id,
                source_name='agent_upload',
                source_id=f'{user.id}_{prop.id}',
                is_active=True,
            )
            db.add(source)
            new_ids.append(prop.id)
            stats['imported'] += 1

        except Exception as e:
            logger.warning("CSV row error: %s", e)
            stats['errors'] += 1

    db.commit()

    # Trigger enrichment for all new properties
    for pid in new_ids:
        _trigger_post_upload(pid)

    return stats


@router.get("", response_model=List[AgentListingResponse])
def list_my_agent_listings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List properties uploaded by this estate agent."""
    check_subscription(user, ['estate_agent', 'white_label', 'admin'])

    props = (
        db.query(Property)
        .join(PropertySource, Property.id == PropertySource.property_id)
        .filter(
            PropertySource.source_name == 'agent_upload',
            PropertySource.source_id.like(f'{user.id}_%'),
        )
        .order_by(Property.date_found.desc())
        .limit(200)
        .all()
    )
    return [
        AgentListingResponse(
            id=p.id, address=p.address, postcode=p.postcode,
            asking_price=p.asking_price, property_type=p.property_type,
            bedrooms=p.bedrooms, status=p.status,
        )
        for p in props
    ]


@router.put("/{property_id}/status")
def update_listing_status(
    property_id: int,
    status: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a listing's status (available, under_offer, sold_stc, exchanged, completed)."""
    check_subscription(user, ['estate_agent', 'white_label', 'admin'])

    # Verify ownership
    source = (
        db.query(PropertySource)
        .filter(
            PropertySource.property_id == property_id,
            PropertySource.source_name == 'agent_upload',
            PropertySource.source_id.like(f'{user.id}_%'),
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail='Listing not found or not yours')

    valid_statuses = {'active', 'under_offer', 'stc', 'sold', 'exchanged', 'completed', 'withdrawn'}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f'Invalid status. Must be one of: {valid_statuses}')

    prop = db.query(Property).get(property_id)
    prop.status = status
    if status in ('stc', 'sold', 'exchanged', 'completed', 'withdrawn'):
        source.is_active = False

    db.commit()
    return {'id': property_id, 'status': status}
