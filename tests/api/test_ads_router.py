"""Tests for ads router and ImgBB client."""
import pytest
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
    client = ImgBBClient(api_key='test-key')

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception('HTTP 500')

    with patch('backend.services.imgbb_client.httpx.post', return_value=mock_response):
        with pytest.raises(Exception):
            client.upload(b'bytes', filename='img.jpg')
