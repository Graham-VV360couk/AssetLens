"""Pydantic schemas for auth endpoints."""
from typing import Optional
from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    company_name: Optional[str] = None
    role: str
    subscription_status: str
    subscription_tier: str
    trial_property_views: int
    trial_ai_views: int
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    company_name: Optional[str] = None
    role: str = 'investor'


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
