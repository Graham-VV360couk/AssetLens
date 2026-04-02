"""Tests for auction house listing upload."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.api.main import app
    return TestClient(app)


def test_create_listing_requires_auth(client):
    """Unauthenticated request should get 401."""
    response = client.post('/api/auction-listings', json={
        'address': '55 Test Lane',
        'postcode': 'LS1 4AP',
    })
    assert response.status_code == 401
