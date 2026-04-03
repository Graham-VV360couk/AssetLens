"""Tests for Stripe webhook handler."""
import pytest
from unittest.mock import patch, MagicMock


def test_subscription_created_updates_user():
    from backend.api.routers.billing import _handle_subscription_created
    db = MagicMock()
    user = MagicMock()
    user.subscription_status = 'trial'
    user.subscription_tier = 'none'
    user.stripe_subscription_id = None
    db.query.return_value.filter.return_value.first.return_value = user

    event_data = {
        'id': 'sub_123',
        'customer': 'cus_123',
        'metadata': {'tier': 'investor'},
        'status': 'active',
    }
    _handle_subscription_created(db, event_data)
    assert user.subscription_status == 'active'
    assert user.subscription_tier == 'investor'


def test_subscription_deleted_cancels_access():
    from backend.api.routers.billing import _handle_subscription_deleted
    db = MagicMock()
    user = MagicMock()
    user.subscription_status = 'active'
    db.query.return_value.filter.return_value.first.return_value = user

    event_data = {'customer': 'cus_123'}
    _handle_subscription_deleted(db, event_data)
    assert user.subscription_status == 'cancelled'


def test_payment_failed_sets_past_due():
    from backend.api.routers.billing import _handle_payment_failed
    db = MagicMock()
    user = MagicMock()
    user.subscription_status = 'active'
    db.query.return_value.filter.return_value.first.return_value = user

    event_data = {'customer': 'cus_123'}
    _handle_payment_failed(db, event_data)
    assert user.subscription_status == 'past_due'
