"""User alert preference model."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class UserAlertPreference(Base, TimestampMixin):
    """
    Stores a user's property alert preferences.
    When new properties arrive, they are scored against each user's
    saved scoring_preferences (on UserProfile) and compared to min_match_pct.
    """
    __tablename__ = 'user_alert_preferences'

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    min_match_pct   = Column(Integer, default=60, nullable=False)  # 0-100
    alert_frequency = Column(String(20), default='daily', nullable=False)  # immediate, daily, weekly
    location_filter = Column(String(200), nullable=True)  # e.g. "WD25,NG1,LS6"
    max_price       = Column(Integer, nullable=True)
    min_beds        = Column(Integer, nullable=True)
    property_types  = Column(String(200), nullable=True)  # e.g. "detached,semi-detached"
    last_alerted_at = Column(DateTime, nullable=True)

    user = relationship('User', backref='alert_preference')

    def __repr__(self):
        return f"<UserAlertPreference(user_id={self.user_id}, min={self.min_match_pct}%, freq={self.alert_frequency})>"
