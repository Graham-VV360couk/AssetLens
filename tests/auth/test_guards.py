"""Tests for subscription-gated route guards."""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException


def _make_user(status='active', tier='investor', is_superuser=False,
               trial_property_views=0, trial_ai_views=0):
    user = MagicMock()
    user.subscription_status = status
    user.subscription_tier = tier
    user.is_superuser = is_superuser
    user.trial_property_views = trial_property_views
    user.trial_ai_views = trial_ai_views
    user.stripe_subscription_id_secondary = None
    return user


def test_admin_bypasses_all():
    from backend.auth.guards import check_subscription
    user = _make_user(is_superuser=True, status='cancelled', tier='none')
    result = check_subscription(user, required_tiers=['investor'])
    assert result is user


def test_active_investor_passes():
    from backend.auth.guards import check_subscription
    user = _make_user(status='active', tier='investor')
    result = check_subscription(user, required_tiers=['investor'])
    assert result is user


def test_cancelled_user_blocked():
    from backend.auth.guards import check_subscription
    user = _make_user(status='cancelled', tier='investor')
    with pytest.raises(HTTPException) as exc:
        check_subscription(user, required_tiers=['investor'])
    assert exc.value.status_code == 403


def test_trial_under_limit_passes():
    from backend.auth.guards import check_subscription
    user = _make_user(status='trial', tier='none', trial_property_views=2)
    result = check_subscription(user, required_tiers=['investor'], trial_type='property_view')
    assert result is user


def test_trial_over_limit_returns_402():
    from backend.auth.guards import check_subscription
    user = _make_user(status='trial', tier='none', trial_property_views=3)
    with pytest.raises(HTTPException) as exc:
        check_subscription(user, required_tiers=['investor'], trial_type='property_view')
    assert exc.value.status_code == 402


def test_wrong_tier_blocked():
    from backend.auth.guards import check_subscription
    user = _make_user(status='active', tier='deal_source')
    with pytest.raises(HTTPException) as exc:
        check_subscription(user, required_tiers=['investor'])
    assert exc.value.status_code == 403


def test_past_due_allowed_with_warning():
    from backend.auth.guards import check_subscription
    user = _make_user(status='past_due', tier='investor')
    result = check_subscription(user, required_tiers=['investor'])
    assert result is user
