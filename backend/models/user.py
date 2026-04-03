"""User and UserProfile models for auth and subscription management."""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin

import enum


class UserRole(str, enum.Enum):
    investor = 'investor'
    auction_house = 'auction_house'
    deal_source = 'deal_source'
    estate_agent = 'estate_agent'
    admin = 'admin'


class SubscriptionStatus(str, enum.Enum):
    trial = 'trial'
    active = 'active'
    past_due = 'past_due'
    cancelled = 'cancelled'


class SubscriptionTier(str, enum.Enum):
    none = 'none'
    investor = 'investor'
    auction_house = 'auction_house'
    deal_source = 'deal_source'
    estate_agent = 'estate_agent'
    white_label = 'white_label'
    admin = 'admin'


class User(Base, TimestampMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)

    role = Column(String(20), nullable=False, default='investor')
    subscription_status = Column(String(20), nullable=False, default='trial')
    subscription_tier = Column(String(20), nullable=False, default='none')

    stripe_customer_id = Column(String(100), unique=True, nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)
    stripe_subscription_id_secondary = Column(String(100), nullable=True)

    trial_property_views = Column(Integer, default=0, nullable=False)
    trial_ai_views = Column(Integer, default=0, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    profile = relationship('UserProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class UserProfile(Base, TimestampMixin):
    __tablename__ = 'user_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False)

    # Financial capacity
    max_deposit = Column(Integer, nullable=True)
    loan_type_sought = Column(String(50), nullable=True)
    max_loan_wanted = Column(Integer, nullable=True)
    loan_term_months = Column(Integer, nullable=True)
    purpose = Column(String(20), nullable=True)

    # Portfolio & experience
    investment_experience = Column(String(20), nullable=True)
    properties_owned = Column(Integer, nullable=True)
    portfolio_value_band = Column(String(20), nullable=True)
    outstanding_mortgage_band = Column(String(20), nullable=True)
    hmo_experience = Column(Boolean, nullable=True)
    development_experience = Column(Boolean, nullable=True)
    limited_company = Column(Boolean, nullable=True)
    company_name_ch = Column(String(200), nullable=True)
    companies_house_number = Column(String(20), nullable=True)
    spv = Column(Boolean, nullable=True)
    personal_guarantee_willing = Column(Boolean, nullable=True)

    # Personal circumstances
    main_residence = Column(Boolean, nullable=True)
    uk_resident = Column(Boolean, nullable=True)
    employment_status = Column(String(20), nullable=True)
    annual_income_band = Column(String(20), nullable=True)
    credit_history = Column(String(20), nullable=True)

    # Investment preferences
    target_location = Column(String(200), nullable=True)
    strategy = Column(String(30), nullable=True)
    readiness = Column(String(20), nullable=True)

    # GDPR
    broker_consent_given_at = Column(DateTime, nullable=True)
    profile_deletion_at = Column(DateTime, nullable=True)

    # Scoring preferences (JSON — slider weights)
    scoring_preferences = Column(Text, nullable=True)

    # Uploader settings
    auction_form_field_prefs = Column(Text, nullable=True)
    brand_logo_url = Column(String(500), nullable=True)
    brand_primary_colour = Column(String(7), nullable=True)
    brand_accent_colour = Column(String(7), nullable=True)
    custom_subdomain = Column(String(200), nullable=True)

    user = relationship('User', back_populates='profile')

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id})>"
