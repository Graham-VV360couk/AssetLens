"""User manager with custom registration logic."""
import logging
from typing import Optional

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from backend.models.user import User, UserProfile, SubscriptionStatus, SubscriptionTier, UserRole

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_user(db: Session, email: str, password: str, full_name: str,
                role: str = 'investor', company_name: str = None) -> User:
    """Create a new user with trial status and empty profile."""
    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name,
        company_name=company_name,
        role=role,
        subscription_status='trial',
        subscription_tier='none',
    )
    db.add(user)
    db.flush()

    profile = UserProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Verify email + password, return User or None."""
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()
