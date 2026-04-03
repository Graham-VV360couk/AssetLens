"""Account settings and investor profile endpoints."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import get_current_user
from backend.models.user import User, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/account", tags=["account"])


class ProfileUpdate(BaseModel):
    max_deposit: Optional[int] = None
    loan_type_sought: Optional[str] = None
    max_loan_wanted: Optional[int] = None
    loan_term_months: Optional[int] = None
    purpose: Optional[str] = None
    investment_experience: Optional[str] = None
    properties_owned: Optional[int] = None
    portfolio_value_band: Optional[str] = None
    outstanding_mortgage_band: Optional[str] = None
    hmo_experience: Optional[bool] = None
    development_experience: Optional[bool] = None
    limited_company: Optional[bool] = None
    company_name_ch: Optional[str] = None
    companies_house_number: Optional[str] = None
    spv: Optional[bool] = None
    personal_guarantee_willing: Optional[bool] = None
    main_residence: Optional[bool] = None
    uk_resident: Optional[bool] = None
    employment_status: Optional[str] = None
    annual_income_band: Optional[str] = None
    credit_history: Optional[str] = None
    target_location: Optional[str] = None
    strategy: Optional[str] = None
    readiness: Optional[str] = None
    scoring_preferences: Optional[str] = None


@router.get("/profile")
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("/profile")
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/profile/consent-broker")
def consent_broker(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.broker_consent_given_at = datetime.utcnow()
    db.commit()
    return {"consented_at": str(profile.broker_consent_given_at)}


@router.delete("/profile/financial")
def delete_financial_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """GDPR: NULL all financial columns but retain account."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    financial_fields = [
        'max_deposit', 'loan_type_sought', 'max_loan_wanted', 'loan_term_months', 'purpose',
        'investment_experience', 'properties_owned', 'portfolio_value_band', 'outstanding_mortgage_band',
        'hmo_experience', 'development_experience', 'limited_company', 'company_name_ch',
        'companies_house_number', 'spv', 'personal_guarantee_willing', 'main_residence',
        'uk_resident', 'employment_status', 'annual_income_band', 'credit_history',
    ]
    for field in financial_fields:
        setattr(profile, field, None)

    profile.profile_deletion_at = datetime.utcnow()
    profile.broker_consent_given_at = None
    db.commit()
    return {"deleted_at": str(profile.profile_deletion_at)}
