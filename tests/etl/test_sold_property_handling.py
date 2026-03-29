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
