"""
EPC Lookup Service

Looks up EPC certificate data for a property:
1. Queries the local epc_certificates DB table (fast, ~24M records from bulk download).
2. Falls back to the live EPC API for certificates not yet in the bulk dataset.

Address matching uses normalised token overlap (fuzzy matching without external deps).
"""
import logging
import os
import re
from typing import Optional

import requests
from sqlalchemy.orm import Session

from backend.models.epc_certificate import EPCCertificate

logger = logging.getLogger(__name__)

EPC_API_BASE = "https://epc.opendatacommunities.org/api/v1/domestic/search"
EPC_API_EMAIL = os.environ.get("EPC_API_EMAIL", "")
EPC_API_KEY = os.environ.get("EPC_API_KEY", "")

# EPC property_type + built_form → AssetLens property_type
EPC_TYPE_MAP = {
    ("House",       "Detached"):      "detached",
    ("House",       "Semi-Detached"): "semi-detached",
    ("House",       "Mid-Terrace"):   "terraced",
    ("House",       "End-Terrace"):   "terraced",
    ("Flat",        None):            "flat",
    ("Maisonette",  None):            "maisonette",
    ("Bungalow",    "Detached"):      "bungalow",
    ("Bungalow",    "Semi-Detached"): "semi-detached bungalow",
    ("Bungalow",    "Mid-Terrace"):   "terraced",
    ("Bungalow",    "End-Terrace"):   "terraced",
}


def _map_epc_type(property_type: Optional[str], built_form: Optional[str]) -> Optional[str]:
    """Map EPC property_type + built_form to an AssetLens property_type string."""
    if not property_type:
        return None
    pt = property_type.strip().title()
    bf = built_form.strip().title() if built_form else None
    mapped = EPC_TYPE_MAP.get((pt, bf))
    if mapped:
        return mapped
    # Fallback: type-only match
    mapped = EPC_TYPE_MAP.get((pt, None))
    return mapped


def _normalise(text: str) -> set:
    """Lowercase, strip punctuation, return token set for overlap scoring."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Expand common abbreviations
    replacements = {
        r'\bst\b': 'street',
        r'\brd\b': 'road',
        r'\bav\b': 'avenue',
        r'\bave\b': 'avenue',
        r'\bdr\b': 'drive',
        r'\bln\b': 'lane',
        r'\bcl\b': 'close',
        r'\bct\b': 'court',
        r'\bpl\b': 'place',
        r'\bgt\b': 'great',
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return set(text.split())


def _address_similarity(candidate_address: str, query_address: str) -> float:
    """Return token overlap ratio between two address strings (0–1)."""
    a = _normalise(candidate_address or '')
    b = _normalise(query_address or '')
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    return intersection / max(len(a), len(b))


def _cert_to_dict(cert: EPCCertificate) -> dict:
    return {
        'lmk_key':        cert.lmk_key,
        'address1':       cert.address1,
        'postcode':       cert.postcode,
        'property_type':  cert.property_type,
        'built_form':     cert.built_form,
        'mapped_type':    _map_epc_type(cert.property_type, cert.built_form),
        'floor_area_sqm': cert.floor_area_sqm,
        'energy_rating':  cert.energy_rating,
        'inspection_date': cert.inspection_date,
    }


def lookup_by_address(
    db: Session,
    postcode: str,
    address: str,
    min_similarity: float = 0.3,
) -> Optional[dict]:
    """
    Return the best-matching EPC certificate for (postcode, address).

    Tries the local DB table first; falls back to the live API if no match
    and API credentials are configured.

    Returns a dict with keys:
        lmk_key, address1, postcode, property_type, built_form, mapped_type,
        floor_area_sqm, energy_rating, inspection_date
    or None if no match found.
    """
    postcode_clean = postcode.strip().upper()
    result = _lookup_local(db, postcode_clean, address, min_similarity)
    if result:
        return result
    # Fallback to live API only if credentials present
    if EPC_API_EMAIL and EPC_API_KEY:
        result = _api_lookup(postcode_clean, address, min_similarity)
    return result


def _lookup_local(
    db: Session,
    postcode: str,
    address: str,
    min_similarity: float,
) -> Optional[dict]:
    """Query the local epc_certificates table."""
    try:
        candidates = (
            db.query(EPCCertificate)
            .filter(EPCCertificate.postcode == postcode)
            .order_by(EPCCertificate.inspection_date.desc())  # prefer most recent
            .limit(50)
            .all()
        )
        if not candidates:
            return None

        best_cert = None
        best_score = min_similarity
        for cert in candidates:
            addr_str = ' '.join(filter(None, [cert.address1, cert.address2]))
            score = _address_similarity(addr_str, address)
            if score > best_score:
                best_score = score
                best_cert = cert

        if best_cert:
            logger.debug(
                "EPC local match: %s → %s (score=%.2f)",
                address, best_cert.address1, best_score,
            )
            return _cert_to_dict(best_cert)
    except Exception as e:
        logger.warning("EPC local lookup error for %s: %s", postcode, e)
    return None


def _api_lookup(postcode: str, address: str, min_similarity: float) -> Optional[dict]:
    """Call the live EPC API as a fallback for missing/new certificates."""
    try:
        resp = requests.get(
            EPC_API_BASE,
            params={"postcode": postcode, "size": 25},
            headers={"Accept": "application/json"},
            auth=(EPC_API_EMAIL, EPC_API_KEY),
            timeout=10,
        )
        if not resp.ok:
            logger.debug("EPC API returned %s for %s", resp.status_code, postcode)
            return None

        rows = resp.json().get("rows", [])
        best = None
        best_score = min_similarity
        for row in rows:
            addr_str = row.get("address1", "") or ""
            score = _address_similarity(addr_str, address)
            if score > best_score:
                best_score = score
                best = row

        if best:
            return {
                'lmk_key':        best.get("lmk-key"),
                'address1':       best.get("address1"),
                'postcode':       best.get("postcode"),
                'property_type':  best.get("property-type"),
                'built_form':     best.get("built-form"),
                'mapped_type':    _map_epc_type(best.get("property-type"), best.get("built-form")),
                'floor_area_sqm': _safe_float(best.get("total-floor-area")),
                'energy_rating':  best.get("current-energy-rating"),
                'inspection_date': None,
            }
    except Exception as e:
        logger.warning("EPC API lookup error for %s: %s", postcode, e)
    return None


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
