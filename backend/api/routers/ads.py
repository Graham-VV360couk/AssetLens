"""Advertising bar config endpoints."""
import json
import logging
import os
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.imgbb_client import ImgBBClient
from backend.services.email_service import EmailAlertService

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/ads', tags=['ads'])

# Resolved at import time; tests monkeypatch this module attribute directly.
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'ad_config.json')
CONFIG_PATH = os.path.normpath(CONFIG_PATH)


def _load_config() -> dict:
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def _require_submit_token(x_submit_token: str = Header(None)) -> None:
    expected = os.environ.get('AD_SUBMIT_TOKEN', '')
    if not expected or x_submit_token != expected:
        raise HTTPException(status_code=401, detail='Invalid or missing submit token')


def _require_admin_token(x_admin_token: str = Header(None)) -> None:
    expected = os.environ.get('AD_ADMIN_TOKEN', '')
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail='Invalid or missing admin token')


@router.get('/config')
def get_live_config():
    """Return the live ad slot. Never exposes the pending slot."""
    config = _load_config()
    return config['live']


@router.post('/submit')
async def submit_ad(
    advertiser_name: str = Form(...),
    strapline: str = Form(...),
    cta_label: str = Form(...),
    cta_url: str = Form(...),
    colour_1: Optional[str] = Form('#1a1a2e'),
    colour_2: Optional[str] = Form('#1a1a2e'),
    logo: UploadFile = File(...),
    _: None = Depends(_require_submit_token),
):
    """Advertiser submits a new ad. Uploads logo to ImgBB, stores as pending."""
    config = _load_config()
    if config.get('pending') is not None:
        raise HTTPException(status_code=409, detail='A submission is already awaiting approval')

    imgbb = ImgBBClient()
    logo_bytes = await logo.read()
    logo_url = imgbb.upload(logo_bytes, filename=logo.filename or 'logo.png')

    pending = {
        'enabled': True,
        'advertiser_name': advertiser_name,
        'strapline': strapline,
        'cta_label': cta_label,
        'cta_url': cta_url,
        'logo_url': logo_url,
        'colour_1': colour_1 or '#1a1a2e',
        'colour_2': colour_2 or '#1a1a2e',
        'text_colour': '#ffffff',
    }
    config['pending'] = pending
    _save_config(config)

    # Notify admin by email (best-effort — don't fail submission if email fails)
    try:
        svc = EmailAlertService()
        svc.send_notification(
            subject=f'AssetLens: New ad submission from {advertiser_name}',
            body=f'A new advertisement has been submitted by {advertiser_name}.\n\nStrapline: {strapline}\nCTA: {cta_label} → {cta_url}\n\nReview and approve at /admin/ads',
        )
    except Exception as e:
        logger.warning('Ad submission email notification failed: %s', e)

    return {'status': 'submitted', 'message': 'Your submission is awaiting approval'}


class ApproveRequest(BaseModel):
    action: Literal['approve', 'reject']


@router.post('/approve')
def approve_ad(
    body: ApproveRequest,
    _: None = Depends(_require_admin_token),
):
    """Admin approves or rejects the pending ad."""
    config = _load_config()
    if config.get('pending') is None:
        raise HTTPException(status_code=404, detail='No pending submission')
    if body.action == 'approve':
        config['live'] = config['pending']
        config['live']['enabled'] = True
    config['pending'] = None
    _save_config(config)
    status_map = {'approve': 'approved', 'reject': 'rejected'}
    return {'status': status_map[body.action], 'live': config['live']}


@router.get('/admin-config')
def get_admin_config(_: None = Depends(_require_admin_token)):
    """Return full config including pending slot. Admin only."""
    return _load_config()


class LiveToggleRequest(BaseModel):
    enabled: bool


@router.patch('/live')
def toggle_live(body: LiveToggleRequest, _: None = Depends(_require_admin_token)):
    """Enable or disable the live ad bar."""
    config = _load_config()
    config['live']['enabled'] = body.enabled
    _save_config(config)
    return {'status': 'updated', 'enabled': body.enabled}


EMPTY_SLOT = {
    'enabled': False,
    'advertiser_name': '',
    'strapline': '',
    'cta_label': '',
    'cta_url': '',
    'logo_url': '',
    'colour_1': '#1a1a2e',
    'colour_2': '#1a1a2e',
    'text_colour': '#ffffff',
}


@router.post('/clear')
def clear_live(_: None = Depends(_require_admin_token)):
    """Clear the live ad slot. The bar goes dark immediately."""
    config = _load_config()
    config['live'] = dict(EMPTY_SLOT)
    _save_config(config)
    return {'status': 'cleared'}
