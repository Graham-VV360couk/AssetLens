"""Tests for ads router and ImgBB client."""
import json
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


# ── ImgBB client tests ────────────────────────────────────────────────────────

def test_imgbb_upload_returns_url_on_success():
    from backend.services.imgbb_client import ImgBBClient
    client = ImgBBClient(api_key='test-key')

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'success': True,
        'data': {'url': 'https://i.ibb.co/abc/image.jpg'}
    }

    with patch('backend.services.imgbb_client.httpx.post', return_value=mock_response):
        url = client.upload(b'fake-image-bytes', filename='test.jpg')

    assert url == 'https://i.ibb.co/abc/image.jpg'


def test_imgbb_upload_raises_on_api_failure():
    from backend.services.imgbb_client import ImgBBClient
    client = ImgBBClient(api_key='test-key')

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'success': False, 'error': {'message': 'bad image'}}

    with patch('backend.services.imgbb_client.httpx.post', return_value=mock_response):
        with pytest.raises(RuntimeError, match='ImgBB upload failed'):
            client.upload(b'bad-bytes', filename='bad.jpg')


def test_imgbb_upload_raises_on_http_error():
    from backend.services.imgbb_client import ImgBBClient
    import httpx
    client = ImgBBClient(api_key='test-key')

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        '500 Server Error', request=MagicMock(), response=MagicMock()
    )

    with patch('backend.services.imgbb_client.httpx.post', return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            client.upload(b'bytes', filename='img.jpg')


# ── Router tests ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_config(tmp_path):
    """Fixture: temp ad_config.json with no live ad and no pending."""
    config = {
        'live': {
            'enabled': False, 'advertiser_name': '', 'strapline': '', 'cta_label': '',
            'cta_url': '', 'logo_url': '', 'colour_1': '#1a1a2e', 'colour_2': '#1a1a2e',
            'text_colour': '#ffffff'
        },
        'pending': None
    }
    p = tmp_path / 'ad_config.json'
    p.write_text(json.dumps(config))
    return str(p)


@pytest.fixture
def test_client(tmp_config, monkeypatch):
    monkeypatch.setenv('AD_SUBMIT_TOKEN', 'submit-secret')
    monkeypatch.setenv('AD_ADMIN_TOKEN', 'admin-secret')
    monkeypatch.setenv('IMGBB_API_KEY', 'test-imgbb-key')

    from backend.api.routers import ads as ads_module
    monkeypatch.setattr(ads_module, 'CONFIG_PATH', tmp_config)

    from backend.api.main import app
    return TestClient(app)


def test_get_config_returns_live_slot(test_client):
    response = test_client.get('/api/ads/config')
    assert response.status_code == 200
    data = response.json()
    assert 'enabled' in data
    assert 'pending' not in data  # pending is never exposed


def test_submit_requires_token(test_client):
    response = test_client.post('/api/ads/submit', data={})
    assert response.status_code == 401


def test_submit_stores_pending(test_client, tmp_config):
    logo_url = 'https://i.ibb.co/logo.png'
    fake_logo = b'\x89PNG\r\n' + b'fake' * 100

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'success': True, 'data': {'url': logo_url}}
    mock_response.raise_for_status = MagicMock()

    with patch('backend.services.imgbb_client.httpx.post', return_value=mock_response):
        response = test_client.post(
            '/api/ads/submit',
            headers={'X-Submit-Token': 'submit-secret'},
            data={
                'advertiser_name': 'Test Co',
                'strapline': 'Bridging from 0.49%',
                'cta_label': 'Get a Quote',
                'cta_url': 'https://testco.com',
                'colour_1': '#0f172a',
                'colour_2': '#1e3a5f',
            },
            files={
                'logo': ('logo.png', fake_logo, 'image/png'),
            },
        )

    assert response.status_code == 200
    config = json.loads(open(tmp_config).read())
    assert config['pending']['advertiser_name'] == 'Test Co'
    assert config['pending']['strapline'] == 'Bridging from 0.49%'
    assert config['pending']['logo_url'] == logo_url
    assert config['pending']['colour_1'] == '#0f172a'
    assert config['pending']['colour_2'] == '#1e3a5f'
    assert config['pending']['enabled'] is True


def test_submit_rejects_if_pending_exists(test_client, tmp_config):
    """Cannot submit a second ad when one is already pending approval."""
    existing = json.loads(open(tmp_config).read())
    existing['pending'] = {'advertiser_name': 'Existing Co', 'strapline': 'Existing'}
    open(tmp_config, 'w').write(json.dumps(existing))

    response = test_client.post(
        '/api/ads/submit',
        headers={'X-Submit-Token': 'submit-secret'},
        data={'advertiser_name': 'New Co', 'strapline': 'New', 'cta_label': 'Go', 'cta_url': 'https://x.com'},
        files={
            'logo': ('logo.png', b'img', 'image/png'),
        },
    )
    assert response.status_code == 409


def test_approve_requires_token(test_client):
    response = test_client.post('/api/ads/approve', json={'action': 'approve'})
    assert response.status_code == 401


def test_approve_promotes_pending_to_live(test_client, tmp_config):
    pending_ad = {
        'enabled': True, 'advertiser_name': 'Approved Co', 'strapline': 'Great deal',
        'cta_label': 'Go', 'cta_url': 'https://approved.com', 'logo_url': 'https://i.ibb.co/logo.png',
        'colour_1': '#0f172a', 'colour_2': '#1e3a5f', 'text_colour': '#fff'
    }
    existing = json.loads(open(tmp_config).read())
    existing['pending'] = pending_ad
    open(tmp_config, 'w').write(json.dumps(existing))

    response = test_client.post(
        '/api/ads/approve',
        headers={'X-Admin-Token': 'admin-secret'},
        json={'action': 'approve'},
    )
    assert response.status_code == 200
    config = json.loads(open(tmp_config).read())
    assert config['live']['advertiser_name'] == 'Approved Co'
    assert config['live']['enabled'] is True
    assert config['pending'] is None


def test_reject_clears_pending(test_client, tmp_config):
    existing = json.loads(open(tmp_config).read())
    existing['pending'] = {'advertiser_name': 'Rejected Co'}
    open(tmp_config, 'w').write(json.dumps(existing))

    response = test_client.post(
        '/api/ads/approve',
        headers={'X-Admin-Token': 'admin-secret'},
        json={'action': 'reject'},
    )
    assert response.status_code == 200
    config = json.loads(open(tmp_config).read())
    assert config['pending'] is None
    assert config['live']['advertiser_name'] == ''  # original empty live untouched


def test_admin_config_requires_token(test_client):
    response = test_client.get('/api/ads/admin-config')
    assert response.status_code == 401


def test_admin_config_returns_full_config(test_client, tmp_config):
    existing = json.loads(open(tmp_config).read())
    existing['pending'] = {'advertiser_name': 'Pending Co'}
    open(tmp_config, 'w').write(json.dumps(existing))

    response = test_client.get(
        '/api/ads/admin-config',
        headers={'X-Admin-Token': 'admin-secret'},
    )
    assert response.status_code == 200
    data = response.json()
    assert 'pending' in data
    assert data['pending']['advertiser_name'] == 'Pending Co'


def test_toggle_live_enables_bar(test_client, tmp_config):
    response = test_client.patch(
        '/api/ads/live',
        headers={'X-Admin-Token': 'admin-secret'},
        json={'enabled': True},
    )
    assert response.status_code == 200
    assert response.json()['enabled'] is True
    config = json.loads(open(tmp_config).read())
    assert config['live']['enabled'] is True
