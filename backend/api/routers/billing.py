"""Stripe billing endpoints — checkout, webhook, portal."""
import os
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import get_current_user
from backend.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/billing", tags=["billing"])

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')


class CheckoutRequest(BaseModel):
    price_id: str
    billing_period: str = 'monthly'


@router.post("/create-checkout-session")
def create_checkout_session(
    req: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create Stripe Checkout Session for subscription."""
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={'user_id': str(user.id), 'role': user.role},
        )
        user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode='subscription',
        line_items=[{'price': req.price_id, 'quantity': 1}],
        success_url=f'{FRONTEND_URL}/account?checkout=success',
        cancel_url=f'{FRONTEND_URL}/account?checkout=cancel',
        metadata={'user_id': str(user.id)},
    )
    return {'checkout_url': session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe webhook receiver."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning("Webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = event['data']['object']
    event_type = event['type']

    if event_type == 'customer.subscription.created':
        _handle_subscription_created(db, data)
    elif event_type == 'customer.subscription.updated':
        _handle_subscription_created(db, data)
    elif event_type == 'customer.subscription.deleted':
        _handle_subscription_deleted(db, data)
    elif event_type == 'invoice.payment_failed':
        _handle_payment_failed(db, data)

    db.commit()
    return {'status': 'ok'}


@router.post("/portal-session")
def create_portal_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create Stripe Customer Portal session for self-serve management."""
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f'{FRONTEND_URL}/account',
    )
    return {'portal_url': session.url}


def _handle_subscription_created(db: Session, data: dict):
    """Handle subscription.created and subscription.updated events."""
    customer_id = data.get('customer')
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        logger.warning("Webhook: no user for customer %s", customer_id)
        return

    tier = data.get('metadata', {}).get('tier', 'investor')
    status = data.get('status', 'active')

    user.subscription_status = 'active' if status == 'active' else status
    user.subscription_tier = tier
    if not user.stripe_subscription_id:
        user.stripe_subscription_id = data.get('id')
    else:
        user.stripe_subscription_id_secondary = data.get('id')


def _handle_subscription_deleted(db: Session, data: dict):
    """Handle subscription.deleted — revoke access immediately."""
    customer_id = data.get('customer')
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return
    user.subscription_status = 'cancelled'


def _handle_payment_failed(db: Session, data: dict):
    """Handle invoice.payment_failed — set past_due with 7-day grace."""
    customer_id = data.get('customer')
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return
    user.subscription_status = 'past_due'
