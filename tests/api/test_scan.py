"""Tests for the scan API endpoint."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.api.main import app
    return TestClient(app)


def test_scan_requires_postcode(client):
    response = client.post('/api/scan', json={'address': '123 High St'})
    assert response.status_code == 422


def test_scan_returns_property_result(client):
    mock_result = {
        'scan_type': 'property',
        'cached': False,
        'property_id': 1,
        'address': '123 High St',
        'postcode': 'SW1A 1AA',
    }
    with patch('backend.api.routers.scan.ScanService') as MockSvc:
        MockSvc.return_value.scan.return_value = mock_result
        response = client.post('/api/scan', json={
            'address': '123 High St',
            'postcode': 'SW1A 1AA',
        })
    assert response.status_code == 200
    data = response.json()
    assert data['scan_type'] == 'property'
    assert data['property_id'] == 1


def test_scan_postcode_only_returns_area(client):
    mock_result = {
        'scan_type': 'area',
        'postcode': 'SW1A 1AA',
        'cached': False,
        'avg_price': 500000,
    }
    with patch('backend.api.routers.scan.ScanService') as MockSvc:
        MockSvc.return_value.scan.return_value = mock_result
        response = client.post('/api/scan', json={'postcode': 'SW1A 1AA'})
    assert response.status_code == 200
    assert response.json()['scan_type'] == 'area'
