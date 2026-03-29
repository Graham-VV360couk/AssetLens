"""ImgBB image hosting client."""
import base64
import logging
import os
import httpx

logger = logging.getLogger(__name__)

IMGBB_UPLOAD_URL = 'https://api.imgbb.com/1/upload'


class ImgBBClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('IMGBB_API_KEY', '')
        if not self.api_key:
            raise ValueError('IMGBB_API_KEY not configured')

    def upload(self, image_bytes: bytes, filename: str) -> str:
        """Upload image bytes to ImgBB. Returns the direct image URL."""
        encoded = base64.b64encode(image_bytes).decode('utf-8')
        response = httpx.post(
            IMGBB_UPLOAD_URL,
            data={'key': self.api_key, 'image': encoded, 'name': filename},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('success'):
            msg = data.get('error', {}).get('message', 'unknown error')
            logger.error('ImgBB upload failed: %s', msg)
            raise RuntimeError(f'ImgBB upload failed: {msg}')
        url = data.get('data', {}).get('url')
        if not url:
            raise RuntimeError('ImgBB upload succeeded but returned no URL')
        return url
