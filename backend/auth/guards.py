"""Subscription-gated dependency injection for route protection."""
import logging
from typing import List, Optional

import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.config import JWT_SECRET
from backend.models.user import User

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
TRIAL_PROPERTY_VIEW_LIMIT = 3
TRIAL_AI_VIEW_LIMIT = 3


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization header."""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(' ', 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).get(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401 for unauthenticated."""
    if not authorization or not authorization.startswith('Bearer '):
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


def check_subscription(
    user,
    required_tiers: List[str],
    trial_type: Optional[str] = None,
) -> object:
    """
    Check user's subscription status and tier.
    Raises 402 for trial limit, 403 for wrong tier/cancelled.
    """
    if user.is_superuser:
        return user

    status = user.subscription_status
    tier = user.subscription_tier

    if status == 'trial':
        if trial_type == 'property_view' and user.trial_property_views >= TRIAL_PROPERTY_VIEW_LIMIT:
            raise HTTPException(status_code=402, detail="Trial limit reached")
        if trial_type == 'ai_view' and user.trial_ai_views >= TRIAL_AI_VIEW_LIMIT:
            raise HTTPException(status_code=402, detail="Trial limit reached")
        return user

    if status == 'cancelled':
        raise HTTPException(status_code=403, detail="Subscription cancelled")

    if status in ('active', 'past_due'):
        if tier in required_tiers or tier == 'admin':
            return user
        raise HTTPException(status_code=403, detail="Plan upgrade required")

    raise HTTPException(status_code=403, detail="Subscription required")


def require_subscription(*tiers: str, trial_type: str = None):
    """
    Dependency factory for route-level subscription gating.

    Usage:
        @router.get("/protected")
        def protected(user = Depends(require_subscription('investor', 'admin'))):
            ...
    """
    def dependency(user: User = Depends(get_current_user)):
        return check_subscription(user, list(tiers), trial_type=trial_type)
    return dependency
