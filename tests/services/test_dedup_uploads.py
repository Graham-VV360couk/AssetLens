"""Tests for dedup handling of uploaded properties (auction/deal source) vs scraped."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from backend.models.property import Property


def _make_db_property(address='123 High Street', postcode='SW1A 1AA'):
    prop = MagicMock(spec=Property)
    prop.id = 1
    prop.address = address
    prop.postcode = postcode
    return prop


def _make_deduplicator(db, existing_properties=None):
    from backend.services.deduplication_service import PropertyDeduplicator
    dedup = PropertyDeduplicator(db)
    return dedup


def test_exact_address_match_finds_duplicate(tmp_path):
    """Uploaded lot with exact same address as scraped property should find the duplicate."""
    db = MagicMock()
    existing = _make_db_property(address='123 High Street', postcode='SW1A 1AA')
    db.query.return_value.filter.return_value.all.return_value = [existing]

    dedup = _make_deduplicator(db)
    result = dedup.find_duplicate(address='123 High Street', postcode='SW1A 1AA')
    assert result is not None


def test_postcode_only_does_not_false_match():
    """Uploaded lot with postcode only (no address) should NOT match an existing property."""
    db = MagicMock()
    existing = _make_db_property(address='123 High Street', postcode='SW1A 1AA')
    db.query.return_value.filter.return_value.all.return_value = [existing]

    dedup = _make_deduplicator(db)
    # Empty address with matching postcode — should NOT match
    result = dedup.find_duplicate(address='', postcode='SW1A 1AA')
    # If address is empty, dedup should return None (no meaningful match possible)
    assert result is None


def test_near_miss_address_matches():
    """Uploaded lot with slight address variation should match via fuzzy matching."""
    db = MagicMock()
    existing = _make_db_property(address='123 High Street', postcode='SW1A 1AA')
    db.query.return_value.filter.return_value.all.return_value = [existing]

    dedup = _make_deduplicator(db)
    result = dedup.find_duplicate(address='123 High St', postcode='SW1A 1AA')
    assert result is not None
