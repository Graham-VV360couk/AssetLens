"""Auth endpoints — register, login, refresh, me."""
import logging
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.config import JWT_SECRET, JWT_LIFETIME_SECONDS, JWT_REFRESH_LIFETIME_SECONDS
from backend.auth.manager import create_user, authenticate_user, get_user_by_email
from backend.auth.schemas import UserRead, UserCreate
from backend.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

ALGORITHM = "HS256"


def _create_token(user_id: int, lifetime: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(seconds=lifetime),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if req.role not in ('investor', 'auction_house', 'deal_source'):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = create_user(
        db, email=req.email, password=req.password,
        full_name=req.full_name, role=req.role,
        company_name=req.company_name,
    )
    return TokenResponse(
        access_token=_create_token(user.id, JWT_LIFETIME_SECONDS),
        refresh_token=_create_token(user.id, JWT_REFRESH_LIFETIME_SECONDS),
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=_create_token(user.id, JWT_LIFETIME_SECONDS),
        refresh_token=_create_token(user.id, JWT_REFRESH_LIFETIME_SECONDS),
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.refresh_token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).get(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=_create_token(user.id, JWT_LIFETIME_SECONDS),
        refresh_token=_create_token(user.id, JWT_REFRESH_LIFETIME_SECONDS),
        user=UserRead.model_validate(user),
    )
