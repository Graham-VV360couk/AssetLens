"""Deal source upload portal — same pattern as auction_listings with extra fields."""
import csv
import io
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import get_current_user, check_subscription
from backend.models.property import Property, PropertySource
from backend.models.user import User
from backend.services.deduplication_service import PropertyDeduplicator
from backend.tasks.enrichment import enrich_property_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/deal-listings", tags=["deal-listings"])


class DealListingCreate(BaseModel):
    address: str
    postcode: str
    asking_price: Optional[float] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    description: Optional[str] = None
    sourcing_fee: Optional[float] = None
    gdv_estimate: Optional[float] = None
    refurb_cost_estimate: Optional[float] = None
    deal_expiry_date: Optional[str] = None


@router.post("", status_code=201)
def create_deal_listing(
    listing: DealListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_subscription(user, ['deal_source', 'white_label', 'admin'])

    dedup = PropertyDeduplicator(db)
    existing = dedup.find_duplicate(address=listing.address, postcode=listing.postcode)
    if existing:
        return {'id': existing.id, 'address': existing.address, 'deduplicated': True}

    prop = Property(
        address=listing.address,
        postcode=listing.postcode.upper().strip(),
        property_type=listing.property_type or 'unknown',
        bedrooms=listing.bedrooms,
        bathrooms=listing.bathrooms,
        asking_price=listing.asking_price,
        description=listing.description,
        status='active',
        date_found=datetime.utcnow(),
    )
    db.add(prop)
    db.flush()

    dedup.add_property_source(prop.id, source_name='deal_upload')
    db.commit()

    try:
        enrich_property_task.delay(prop.id)
    except Exception as e:
        logger.warning("Failed to queue enrichment for %d: %s", prop.id, e)

    return {
        'id': prop.id,
        'address': prop.address,
        'postcode': prop.postcode,
        'deduplicated': False,
    }


@router.post("/upload-csv")
async def upload_deal_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_subscription(user, ['deal_source', 'white_label', 'admin'])

    content = await file.read()
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))

    stats = {'imported': 0, 'duplicates': 0, 'errors': 0}
    dedup = PropertyDeduplicator(db)

    for row in reader:
        try:
            address = row.get('address', '').strip()
            postcode = row.get('postcode', '').strip().upper()
            if not postcode:
                stats['errors'] += 1
                continue

            existing = dedup.find_duplicate(address=address, postcode=postcode)
            if existing:
                stats['duplicates'] += 1
                continue

            prop = Property(
                address=address,
                postcode=postcode,
                property_type=row.get('property_type', 'unknown'),
                bedrooms=int(row['bedrooms']) if row.get('bedrooms') else None,
                asking_price=float(row['asking_price']) if row.get('asking_price') else None,
                description=row.get('description'),
                status='active',
                date_found=datetime.utcnow(),
            )
            db.add(prop)
            db.flush()
            dedup.add_property_source(prop.id, source_name='deal_upload')
            stats['imported'] += 1

            try:
                enrich_property_task.delay(prop.id)
            except Exception:
                pass

        except Exception as e:
            logger.warning("CSV row error: %s", e)
            stats['errors'] += 1

    db.commit()
    return stats


@router.get("")
def list_my_deal_listings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_subscription(user, ['deal_source', 'white_label', 'admin'])
    props = (
        db.query(Property)
        .join(PropertySource, Property.id == PropertySource.property_id)
        .filter(PropertySource.source_name == 'deal_upload')
        .order_by(Property.date_found.desc())
        .limit(100)
        .all()
    )
    return [{'id': p.id, 'address': p.address, 'postcode': p.postcode, 'asking_price': p.asking_price} for p in props]
