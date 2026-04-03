"""Private sale listings and double opt-in messaging API."""
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
from backend.models.user_property import UserProperty
from backend.models.property import Property, PropertySource
from backend.models.private_listing import PrivateListing, Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/private-sales", tags=["private-sales"])


# ============================================================================
# Schemas
# ============================================================================

class CreateListingRequest(BaseModel):
    user_property_id: int
    asking_price: float
    description: Optional[str] = None
    photos: Optional[List[str]] = None  # list of image URLs


class ListingResponse(BaseModel):
    id: int
    user_property_id: int
    asking_price: float
    description: Optional[str] = None
    photos: Optional[List[str]] = None
    status: str
    address: Optional[str] = None
    postcode: Optional[str] = None
    town: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    conversation_count: int = 0
    created_at: Optional[datetime] = None


class ConversationResponse(BaseModel):
    id: int
    listing_id: int
    buyer_alias: str  # anonymous — "Buyer #X"
    seller_alias: str
    status: str
    buyer_opted_in: bool
    seller_opted_in: bool
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    id: int
    sender_alias: str
    body: str
    is_mine: bool
    is_read: bool
    created_at: Optional[datetime] = None


class SendMessageRequest(BaseModel):
    body: str


# ============================================================================
# Private listing endpoints
# ============================================================================

@router.post("/listings", status_code=201, response_model=ListingResponse)
def create_listing(
    data: CreateListingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List a property from your portfolio for private sale."""
    # Verify ownership
    user_prop = db.query(UserProperty).filter(
        UserProperty.id == data.user_property_id,
        UserProperty.user_id == user.id,
    ).first()
    if not user_prop:
        raise HTTPException(status_code=404, detail='Property not found in your portfolio')

    # Check not already listed
    existing = db.query(PrivateListing).filter(
        PrivateListing.user_property_id == data.user_property_id,
        PrivateListing.status == 'active',
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail='This property is already listed for sale')

    # Create a Property record so it appears in search results
    prop = Property(
        address=user_prop.address_line1,
        postcode=user_prop.postcode.upper().strip(),
        town=user_prop.town,
        property_type=user_prop.property_type or 'other',
        bedrooms=user_prop.bedrooms,
        bathrooms=user_prop.bathrooms,
        asking_price=data.asking_price,
        description=data.description,
        image_urls=json.dumps(data.photos) if data.photos else None,
        image_url=data.photos[0] if data.photos else None,
        status='active',
        date_found=datetime.utcnow(),
    )
    db.add(prop)
    db.flush()

    # Track source
    source = PropertySource(
        property_id=prop.id,
        source_name='private_sale',
        source_id=f'{user.id}_{user_prop.id}',
        is_active=True,
    )
    db.add(source)

    # Create the private listing
    listing = PrivateListing(
        user_property_id=user_prop.id,
        seller_id=user.id,
        property_id=prop.id,
        asking_price=data.asking_price,
        description=data.description,
        photos_json=json.dumps(data.photos) if data.photos else None,
        status='active',
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    # Trigger enrichment
    try:
        from backend.services.neighbourhood_service import enrich_property
        enrich_property(db, prop)
        db.commit()
    except Exception:
        pass

    return _listing_response(listing, user_prop, db)


@router.get("/listings", response_model=List[ListingResponse])
def my_listings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all my private sale listings."""
    listings = db.query(PrivateListing).filter(
        PrivateListing.seller_id == user.id,
    ).order_by(PrivateListing.created_at.desc()).all()

    return [_listing_response(l, l.user_property, db) for l in listings]


@router.put("/listings/{listing_id}/status")
def update_listing_status(
    listing_id: int,
    status: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update listing status: active, under_offer, sold, withdrawn."""
    listing = db.query(PrivateListing).filter(
        PrivateListing.id == listing_id,
        PrivateListing.seller_id == user.id,
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail='Listing not found')

    valid = {'active', 'under_offer', 'sold', 'withdrawn'}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f'Invalid status: {valid}')

    listing.status = status
    listing.updated_at = datetime.utcnow()

    # Update the linked property record too
    if listing.property_id:
        prop = db.query(Property).get(listing.property_id)
        if prop:
            prop.status = 'stc' if status in ('under_offer', 'sold') else status

    db.commit()
    return {'id': listing_id, 'status': status}


# ============================================================================
# Buyer interest + conversations
# ============================================================================

@router.post("/listings/{listing_id}/interest", response_model=ConversationResponse)
def register_interest(
    listing_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Register interest in a property — initiates double opt-in."""
    listing = db.query(PrivateListing).filter(
        PrivateListing.id == listing_id,
        PrivateListing.status == 'active',
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail='Listing not found or not active')

    if listing.seller_id == user.id:
        raise HTTPException(status_code=400, detail="You can't register interest in your own property")

    # Check if already registered
    existing = db.query(Conversation).filter(
        Conversation.listing_id == listing_id,
        Conversation.buyer_id == user.id,
    ).first()
    if existing:
        return _conversation_response(existing, user.id)

    # Create conversation — buyer opted in, seller pending
    conv = Conversation(
        listing_id=listing_id,
        buyer_id=user.id,
        seller_id=listing.seller_id,
        buyer_opted_in=True,
        seller_opted_in=False,
        status='pending',
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    logger.info('Buyer %d registered interest in listing %d', user.id, listing_id)
    return _conversation_response(conv, user.id)


@router.get("/conversations", response_model=List[ConversationResponse])
def my_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all my conversations (as buyer or seller)."""
    from sqlalchemy import or_
    convs = db.query(Conversation).filter(
        or_(Conversation.buyer_id == user.id, Conversation.seller_id == user.id)
    ).order_by(Conversation.updated_at.desc()).all()

    return [_conversation_response(c, user.id) for c in convs]


@router.post("/conversations/{conv_id}/approve", response_model=ConversationResponse)
def approve_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seller approves a conversation — double opt-in complete, messaging opens."""
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.seller_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail='Conversation not found')

    conv.seller_opted_in = True
    conv.status = 'active'
    conv.updated_at = datetime.utcnow()
    db.commit()

    logger.info('Seller approved conversation %d', conv_id)
    return _conversation_response(conv, user.id)


@router.post("/conversations/{conv_id}/close")
def close_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Either party can close a conversation."""
    from sqlalchemy import or_
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        or_(Conversation.buyer_id == user.id, Conversation.seller_id == user.id),
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail='Conversation not found')

    conv.status = 'closed'
    conv.updated_at = datetime.utcnow()
    db.commit()
    return {'id': conv_id, 'status': 'closed'}


# ============================================================================
# Messages
# ============================================================================

@router.get("/conversations/{conv_id}/messages", response_model=List[MessageResponse])
def get_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    from sqlalchemy import or_
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        or_(Conversation.buyer_id == user.id, Conversation.seller_id == user.id),
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail='Conversation not found')

    if not conv.is_active:
        raise HTTPException(status_code=403, detail='Conversation is not active — both parties must opt in')

    # Mark unread messages as read
    db.query(Message).filter(
        Message.conversation_id == conv_id,
        Message.sender_id != user.id,
        Message.is_read == False,
    ).update({'is_read': True})
    db.commit()

    messages = db.query(Message).filter(
        Message.conversation_id == conv_id,
    ).order_by(Message.created_at).all()

    is_buyer = user.id == conv.buyer_id
    return [
        MessageResponse(
            id=m.id,
            sender_alias='You' if m.sender_id == user.id else ('Buyer' if not is_buyer else 'Seller'),
            body=m.body,
            is_mine=m.sender_id == user.id,
            is_read=m.is_read,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/conversations/{conv_id}/messages", status_code=201, response_model=MessageResponse)
def send_message(
    conv_id: int,
    data: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a message in an active conversation."""
    from sqlalchemy import or_
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        or_(Conversation.buyer_id == user.id, Conversation.seller_id == user.id),
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail='Conversation not found')

    if not conv.is_active:
        raise HTTPException(status_code=403, detail='Conversation is not active — both parties must opt in')

    if not data.body or not data.body.strip():
        raise HTTPException(status_code=400, detail='Message cannot be empty')

    msg = Message(
        conversation_id=conv_id,
        sender_id=user.id,
        body=data.body.strip()[:2000],  # max 2000 chars
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)

    is_buyer = user.id == conv.buyer_id
    return MessageResponse(
        id=msg.id,
        sender_alias='You',
        body=msg.body,
        is_mine=True,
        is_read=False,
        created_at=msg.created_at,
    )


# ============================================================================
# Helpers
# ============================================================================

def _listing_response(listing: PrivateListing, user_prop: UserProperty, db: Session) -> ListingResponse:
    conv_count = db.query(Conversation).filter(Conversation.listing_id == listing.id).count()
    photos = None
    if listing.photos_json:
        try:
            photos = json.loads(listing.photos_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return ListingResponse(
        id=listing.id,
        user_property_id=listing.user_property_id,
        asking_price=listing.asking_price,
        description=listing.description,
        photos=photos,
        status=listing.status,
        address=user_prop.address_line1 if user_prop else None,
        postcode=user_prop.postcode if user_prop else None,
        town=user_prop.town if user_prop else None,
        property_type=user_prop.property_type if user_prop else None,
        bedrooms=user_prop.bedrooms if user_prop else None,
        conversation_count=conv_count,
        created_at=listing.created_at,
    )


def _conversation_response(conv: Conversation, viewer_id: int) -> ConversationResponse:
    is_buyer = viewer_id == conv.buyer_id
    unread = 0
    last_msg = None
    last_msg_at = None

    if conv.messages:
        unread = sum(1 for m in conv.messages if not m.is_read and m.sender_id != viewer_id)
        last = conv.messages[-1] if conv.messages else None
        if last:
            last_msg = last.body[:100]
            last_msg_at = last.created_at

    return ConversationResponse(
        id=conv.id,
        listing_id=conv.listing_id,
        buyer_alias=f'Buyer #{conv.buyer_id}' if not is_buyer else 'You',
        seller_alias=f'Seller #{conv.seller_id}' if is_buyer else 'You',
        status=conv.status,
        buyer_opted_in=conv.buyer_opted_in,
        seller_opted_in=conv.seller_opted_in,
        unread_count=unread,
        last_message=last_msg,
        last_message_at=last_msg_at,
        created_at=conv.created_at,
    )
