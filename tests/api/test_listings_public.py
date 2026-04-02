"""Tests for public listing page API — field visibility rules."""
import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.api.main import app
    return TestClient(app)


def test_public_listing_hides_full_address(client):
    """Public view should show only town/area, not full address."""
    mock_prop = MagicMock()
    mock_prop.id = 1
    mock_prop.address = '123 High Street'
    mock_prop.postcode = 'SW1A 1AA'
    mock_prop.town = 'London'
    mock_prop.asking_price = 300000
    mock_prop.property_type = 'flat'
    mock_prop.bedrooms = 2
    mock_prop.bathrooms = 1
    mock_prop.description = 'Nice flat'
    mock_prop.image_urls = '["img1.jpg","img2.jpg","img3.jpg","img4.jpg"]'
    mock_prop.score = None

    with patch('backend.api.routers.listings._get_listing_property', return_value=mock_prop):
        response = client.get('/api/listings/1')

    assert response.status_code == 200
    data = response.json()
    assert data['address'] == 'London'
    assert data['postcode'] == 'SW1A'
    assert data.get('ai_score') is None
    assert len(data.get('photos', [])) <= 3
