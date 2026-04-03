"""
Junk Property Cleanup Script

Identifies and archives properties that aren't real addresses:
- Auction status text ("Auction Ended -22 Jan 2026")
- Lot timers ("Lot10| End Time -25/03/2026")
- Fee/status messages ("Reservation Fee Property - Sale Agreed")
- Descriptions with no address ("COASTAL LAND WITH PLANNING")

For borderline cases with partial addresses (e.g. "12 Belfield Avenue, Marldon"),
attempts geocoding via postcodes.io to recover a postcode.

Usage:
    python scripts/cleanup_junk_properties.py --dry-run     # preview
    python scripts/cleanup_junk_properties.py --commit       # archive junk, geocode partials
"""
import argparse
import logging
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
from sqlalchemy import func, or_
from backend.models.base import SessionLocal
from backend.models.property import Property
from backend.models.postcode import Postcode

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Patterns that indicate junk, not an address
JUNK_PATTERNS = [
    re.compile(r'auction\s*(ended|ends|end\s*time)', re.IGNORECASE),
    re.compile(r'^lot\s*\d', re.IGNORECASE),
    re.compile(r'end\s*time\s*[-:]', re.IGNORECASE),
    re.compile(r'reservation\s*fee', re.IGNORECASE),
    re.compile(r'sale\s*agreed\s*for', re.IGNORECASE),
    re.compile(r'^\d{1,2}[:/]\d{2}', re.IGNORECASE),  # time format
    re.compile(r'^\d{1,2}\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', re.IGNORECASE),
]

# Patterns that suggest a real address (even partial)
ADDRESS_INDICATORS = [
    re.compile(r'\b(road|street|lane|drive|close|avenue|way|crescent|gardens|terrace|'
               r'place|court|mews|hill|park|grove|square|row|walk|rise|view|'
               r'parade|passage|yard|wharf|quay)\b', re.IGNORECASE),
    re.compile(r'\b(flat|house|cottage|apartment|bungalow)\b', re.IGNORECASE),
    re.compile(r'^\d+[a-z]?\s+\w', re.IGNORECASE),  # starts with house number
]

POSTCODE_RE = re.compile(r'([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})', re.IGNORECASE)


def _is_junk(address: str) -> bool:
    """Return True if the address text is clearly not a real address."""
    if not address or len(address.strip()) < 5:
        return True
    for pattern in JUNK_PATTERNS:
        if pattern.search(address):
            return True
    return False


def _looks_like_address(text: str) -> bool:
    """Return True if the text contains address-like patterns."""
    for pattern in ADDRESS_INDICATORS:
        if pattern.search(text):
            return True
    return False


def _geocode_address(address: str) -> dict | None:
    """Try to geocode a partial address via postcodes.io."""
    # postcodes.io doesn't do address geocoding, but we can try Google-style
    # For now, try to find a town/area name and look up postcodes near it
    # This is a best-effort approach
    try:
        # Use postcodes.io /postcodes?lon=&lat= if we had coords
        # Instead, try their /places endpoint for place names
        # Extract the last meaningful part (usually the town)
        parts = [p.strip() for p in address.split(',') if p.strip()]
        for part in reversed(parts):
            # Skip parts that are just numbers or property types
            if re.match(r'^\d+$', part) or len(part) < 3:
                continue
            resp = requests.get(
                f'https://api.postcodes.io/places?q={part}&limit=1',
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                results = data.get('result', [])
                if results:
                    place = results[0]
                    return {
                        'latitude': place.get('latitude'),
                        'longitude': place.get('longitude'),
                        'name': place.get('name_1'),
                    }
    except Exception:
        pass
    return None


def classify_properties(db, dry_run: bool):
    """Classify empty-postcode properties as junk, partial address, or unknown."""
    props = db.query(Property).filter(
        or_(Property.postcode.is_(None), Property.postcode == '')
    ).all()

    junk = []
    partial = []
    unknown = []

    for p in props:
        addr = p.address or ''
        if _is_junk(addr):
            junk.append(p)
        elif _looks_like_address(addr):
            partial.append(p)
        else:
            unknown.append(p)

    logger.info('Classification: %d junk, %d partial addresses, %d unknown', len(junk), len(partial), len(unknown))

    # Archive junk
    archived = 0
    for p in junk:
        logger.debug('JUNK id=%d: "%s"', p.id, (p.address or '')[:60])
        if not dry_run:
            p.status = 'archived'
        archived += 1

    if not dry_run:
        db.commit()
    logger.info('Archived %d junk properties', archived)

    # Try to geocode partial addresses
    geocoded = 0
    for p in partial:
        addr = p.address or ''
        logger.info('PARTIAL id=%d: "%s"', p.id, addr[:80])

        # First check if there's a postcode district in the address (e.g. "EX22")
        district_match = re.search(r'\b([A-Z]{1,2}\d{1,2})\b', addr)
        if district_match:
            district = district_match.group(1).upper()
            # Look up any postcode in that district from our table
            sample_pc = db.query(Postcode).filter(
                Postcode.postcode.like(f'{district}%'),
                Postcode.latitude.isnot(None),
            ).first()
            if sample_pc:
                logger.info('  -> District match: %s -> %s (%.4f, %.4f)',
                            district, sample_pc.postcode, sample_pc.latitude, sample_pc.longitude)
                if not dry_run:
                    p.postcode = sample_pc.postcode
                    p.latitude = sample_pc.latitude
                    p.longitude = sample_pc.longitude
                geocoded += 1
                continue

        # Try postcodes.io place lookup
        result = _geocode_address(addr)
        if result and result.get('latitude'):
            # Find nearest postcode to those coordinates
            lat, lng = result['latitude'], result['longitude']
            nearest = db.query(Postcode).filter(
                Postcode.latitude.between(lat - 0.01, lat + 0.01),
                Postcode.longitude.between(lng - 0.01, lng + 0.01),
                Postcode.latitude.isnot(None),
            ).first()
            if nearest:
                logger.info('  -> Place lookup: %s -> %s (%.4f, %.4f)',
                            result.get('name'), nearest.postcode, nearest.latitude, nearest.longitude)
                if not dry_run:
                    p.postcode = nearest.postcode
                    p.latitude = nearest.latitude
                    p.longitude = nearest.longitude
                geocoded += 1
                continue

        logger.info('  -> Could not geocode')
        time.sleep(0.2)  # rate limit postcodes.io

    if not dry_run:
        db.commit()

    # Log unknowns
    for p in unknown[:10]:
        logger.info('UNKNOWN id=%d: "%s"', p.id, (p.address or '')[:80])

    logger.info('=== SUMMARY ===')
    logger.info('Junk archived:     %d', archived)
    logger.info('Partial geocoded:  %d', geocoded)
    logger.info('Unknown remaining: %d', len(unknown))
    logger.info('Partial remaining: %d (of %d)', len(partial) - geocoded, len(partial))

    return archived, geocoded


def main():
    parser = argparse.ArgumentParser(description='Clean up junk property records')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true', help='Preview without changes')
    group.add_argument('--commit', action='store_true', help='Apply changes')
    args = parser.parse_args()

    if args.dry_run:
        logger.info('=== DRY RUN ===')

    db = SessionLocal()
    try:
        classify_properties(db, dry_run=args.dry_run)
    finally:
        db.close()


if __name__ == '__main__':
    main()
