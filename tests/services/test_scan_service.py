"""Tests for on-demand property scan service."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, date


def _make_scan_service(db):
    from backend.services.scan_service import ScanService
    svc = ScanService(db)
    return svc


def test_cached_property_returned_without_api_calls():
    """If property already exists in DB, return it without calling external APIs."""
    db = MagicMock()
    from backend.models.property import Property
    existing = MagicMock(spec=Property)
    existing.id = 1
    existing.address = '123 High St'
    existing.postcode = 'SW1A 1AA'
    existing.status = 'active'
    existing.score = MagicMock()
    existing.ai_insight = MagicMock()

    svc = _make_scan_service(db)
    with patch.object(svc, '_find_existing', return_value=existing):
        result = svc.scan(address='123 High St', postcode='SW1A 1AA')
    assert result['property_id'] == 1
    assert result['scan_type'] == 'property'
    assert result['cached'] is True


def test_postcode_only_returns_area_scan():
    """Postcode without address returns area-level data only."""
    db = MagicMock()
    svc = _make_scan_service(db)
    with patch.object(svc, '_find_existing', return_value=None), \
         patch.object(svc, '_area_scan', return_value={'avg_price': 250000}):
        result = svc.scan(address='', postcode='SW1A 1AA')
    assert result['scan_type'] == 'area'


def test_new_property_created_and_enriched():
    """A property not in DB gets created, scored, and queued for AI analysis."""
    db = MagicMock()
    svc = _make_scan_service(db)
    with patch.object(svc, '_find_existing', return_value=None), \
         patch.object(svc, '_create_scanned_property', return_value=MagicMock(id=99)) as mock_create, \
         patch.object(svc, '_enrich_property') as mock_enrich, \
         patch.object(svc, '_score_property') as mock_score:
        result = svc.scan(address='456 New Road', postcode='LS1 4AP')
    mock_create.assert_called_once()
    mock_enrich.assert_called_once()
    mock_score.assert_called_once()
    assert result['scan_type'] == 'property'
    assert result['cached'] is False
