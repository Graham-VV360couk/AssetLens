"""Tests for status mapping and sold property handling in the feed importer."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

# ── Status mapping tests ──────────────────────────────────────────────────────

def make_client():
    from backend.services.searchland_client import SearchlandClient
    client = SearchlandClient.__new__(SearchlandClient)
    return client


def normalize(raw_status):
    client = make_client()
    raw = {
        'id': '123',
        'url': 'http://example.com',
        'address': {'display_address': '1 Test St', 'postcode': 'SW1A 1AA',
                    'town': 'London', 'county': 'Greater London'},
        'property_type': 'flat',
        'bedrooms': 2,
        'bathrooms': 1,
        'price': 300000,
        'description': '',
        'status': raw_status,
        'sold_price': None,
    }
    return client.normalize_property_data(raw)


@pytest.mark.parametrize('raw_status', ['for_sale', 'available', None, 'unknown_future_value'])
def test_active_statuses_map_to_active(raw_status):
    result = normalize(raw_status)
    assert result['status'] == 'active'


@pytest.mark.parametrize('raw_status', ['stc', 'sold_stc', 'under_offer', 'sale_agreed'])
def test_stc_statuses_map_to_stc(raw_status):
    result = normalize(raw_status)
    assert result['status'] == 'stc'


@pytest.mark.parametrize('raw_status', ['sold', 'completed'])
def test_sold_statuses_map_to_sold(raw_status):
    result = normalize(raw_status)
    assert result['status'] == 'sold'


def test_sold_price_passed_through():
    client = make_client()
    raw = {
        'id': '123', 'url': 'http://example.com',
        'address': {'display_address': '1 Test St', 'postcode': 'SW1A 1AA',
                    'town': 'London', 'county': 'Greater London'},
        'property_type': 'flat', 'bedrooms': 2, 'bathrooms': 1,
        'price': 300000, 'description': '', 'status': 'sold', 'sold_price': 285000,
    }
    result = client.normalize_property_data(raw)
    assert result['sold_price'] == 285000


# ── Importer branching tests ──────────────────────────────────────────────────

from backend.models.property import Property, PropertySource
from backend.models.sales_history import SalesHistory


def _make_property(status='active', asking_price=300000):
    prop = Property(
        id=1, address='1 Test St', postcode='SW1A 1AA',
        property_type='flat', bedrooms=2, status=status,
        asking_price=asking_price, date_found=date.today(),
    )
    return prop


def _make_importer(db):
    from backend.etl.licensed_feed_importer import LicensedFeedImporter
    importer = LicensedFeedImporter.__new__(LicensedFeedImporter)
    importer.db = db
    importer.stats = {'new': 0, 'updated': 0, 'errors': 0, 'skipped': 0, 'fetched': 0}
    return importer


def test_stc_status_updates_property_status():
    """An STC property in the feed updates the property status to 'stc' and stays visible."""
    db = MagicMock()
    prop = _make_property(status='active')
    importer = _make_importer(db)
    importer._apply_status_change(prop, 'stc', sold_price=None)
    assert prop.status == 'stc'
    assert prop.date_sold is None


def test_sold_status_archives_property():
    """A sold property gets archived and date_sold set."""
    db = MagicMock()
    prop = _make_property(status='active', asking_price=300000)
    importer = _make_importer(db)
    importer._apply_status_change(prop, 'sold', sold_price=285000)
    assert prop.status == 'sold'
    assert prop.date_sold == date.today()
    db.add.assert_called_once()
    sales_record = db.add.call_args[0][0]
    assert isinstance(sales_record, SalesHistory)
    assert sales_record.sale_price == 285000


def test_sold_without_price_uses_none():
    """A sold property with no confirmed price stores sale_price=None."""
    db = MagicMock()
    prop = _make_property(status='active', asking_price=300000)
    importer = _make_importer(db)
    importer._apply_status_change(prop, 'sold', sold_price=None)
    assert prop.status == 'sold'
    db.add.assert_called_once()
    sales_record = db.add.call_args[0][0]
    assert sales_record.sale_price is None


def test_active_status_no_change():
    """An active property coming through the feed makes no status change."""
    db = MagicMock()
    prop = _make_property(status='active')
    importer = _make_importer(db)
    importer._apply_status_change(prop, 'active', sold_price=None)
    assert prop.status == 'active'
    db.add.assert_not_called()
