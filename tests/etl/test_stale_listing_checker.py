"""Tests for stale listing checker ETL job."""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, date


def _make_stale_property(days_old=10):
    prop = MagicMock()
    prop.id = 1
    prop.address = '1 Test St'
    prop.postcode = 'SW1A 1AA'
    prop.property_type = 'flat'
    prop.status = 'active'
    prop.asking_price = 300000
    prop.date_sold = None
    source = MagicMock()
    source.source_name = 'searchland'
    source.source_id = 'SL123'
    source.last_seen_at = datetime.utcnow() - timedelta(days=days_old)
    prop.sources = [source]
    return prop


def test_fresh_properties_are_skipped():
    """Properties last seen within 7 days are not re-fetched."""
    from backend.etl.stale_listing_checker import StaleListingChecker
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    checker = StaleListingChecker(db)
    stats = checker.run()
    assert stats['rechecked'] == 0


def test_stale_active_property_is_rechecked():
    """A property not seen for 8 days is included in the recheck batch."""
    from backend.etl.stale_listing_checker import StaleListingChecker
    stale_prop = _make_stale_property(days_old=8)
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.all.return_value = [stale_prop]

    with patch.object(StaleListingChecker, '_recheck_property', return_value='active') as mock_recheck:
        checker = StaleListingChecker(db)
        stats = checker.run()

    mock_recheck.assert_called_once_with(stale_prop)
    assert stats['rechecked'] == 1


def test_sold_outcome_archives_property():
    """When re-check returns 'sold', property is archived."""
    from backend.etl.stale_listing_checker import StaleListingChecker
    from backend.models.sales_history import SalesHistory
    stale_prop = _make_stale_property(days_old=10)
    db = MagicMock()

    checker = StaleListingChecker(db)
    checker._apply_sold(stale_prop, sold_price=None)

    assert stale_prop.status == 'sold'
    assert stale_prop.date_sold == date.today()
    db.add.assert_called_once()
    record = db.add.call_args[0][0]
    assert isinstance(record, SalesHistory)


def test_stc_outcome_updates_status():
    """When re-check returns 'stc', property status is set to stc."""
    from backend.etl.stale_listing_checker import StaleListingChecker
    stale_prop = _make_stale_property(days_old=10)
    db = MagicMock()
    checker = StaleListingChecker(db)
    checker._apply_stc(stale_prop)
    assert stale_prop.status == 'stc'
