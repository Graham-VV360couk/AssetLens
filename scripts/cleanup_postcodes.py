"""
Postcode Cleanup Script

Fixes data quality issues in the properties table:
1. Corrupted postcodes (trailing &, non-alpha chars)
2. Empty postcodes (extract from address text)
3. Missing coordinates (backfill from local postcodes table)
4. Re-enrich fixed properties with neighbourhood data

Usage:
    python scripts/cleanup_postcodes.py --dry-run     # preview changes
    python scripts/cleanup_postcodes.py --commit       # apply changes
    python scripts/cleanup_postcodes.py --commit --enrich  # apply + re-enrich
"""
import argparse
import logging
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import func
from backend.models.base import SessionLocal
from backend.models.property import Property
from backend.models.postcode import Postcode

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

POSTCODE_RE = re.compile(r'([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})', re.IGNORECASE)


def _validate_postcode(db, postcode: str) -> str | None:
    """Check if a postcode exists in our ONSPD table. Returns formatted version or None."""
    normalised = re.sub(r'\s+', '', postcode.upper())
    pc = db.query(Postcode).filter(
        func.replace(Postcode.postcode, ' ', '') == normalised
    ).first()
    if pc:
        return pc.postcode  # return the ONSPD-formatted version
    return None


def phase1_fix_corrupted(db, dry_run: bool) -> list[int]:
    """Fix postcodes with trailing junk characters."""
    fixed_ids = []
    props = db.query(Property).filter(
        Property.postcode.isnot(None),
        Property.postcode != '',
    ).all()

    for p in props:
        # Check for non-alphanumeric/space characters
        if re.search(r'[^A-Za-z0-9\s]', p.postcode):
            match = POSTCODE_RE.search(p.postcode)
            if match:
                cleaned = match.group(1).upper().strip()
                validated = _validate_postcode(db, cleaned)
                if validated:
                    logger.info(
                        'CORRUPTED id=%d: "%s" -> "%s"',
                        p.id, p.postcode, validated,
                    )
                    if not dry_run:
                        p.postcode = validated
                    fixed_ids.append(p.id)
                else:
                    logger.warning(
                        'CORRUPTED id=%d: "%s" -> extracted "%s" but not in ONSPD',
                        p.id, p.postcode, cleaned,
                    )
            else:
                logger.warning(
                    'CORRUPTED id=%d: "%s" -> no valid postcode found',
                    p.id, p.postcode,
                )

    return fixed_ids


def phase2_extract_from_address(db, dry_run: bool) -> list[int]:
    """Try to extract postcodes from address text for empty-postcode properties."""
    fixed_ids = []
    props = db.query(Property).filter(
        (Property.postcode.is_(None)) | (Property.postcode == '')
    ).all()

    logger.info('Phase 2: %d properties with empty postcodes', len(props))

    for p in props:
        if not p.address:
            continue
        match = POSTCODE_RE.search(p.address)
        if match:
            candidate = match.group(1).upper().strip()
            validated = _validate_postcode(db, candidate)
            if validated:
                logger.info(
                    'EXTRACTED id=%d: address="%s" -> postcode="%s"',
                    p.id, p.address[:60], validated,
                )
                if not dry_run:
                    p.postcode = validated
                fixed_ids.append(p.id)

    return fixed_ids


def phase3_backfill_coords(db, dry_run: bool) -> list[int]:
    """Backfill lat/lng from local postcodes table."""
    fixed_ids = []
    props = db.query(Property).filter(
        Property.latitude.is_(None),
        Property.postcode.isnot(None),
        Property.postcode != '',
    ).all()

    logger.info('Phase 3: %d properties with postcode but no coordinates', len(props))

    for p in props:
        normalised = re.sub(r'\s+', '', p.postcode.upper())
        pc = db.query(Postcode).filter(
            func.replace(Postcode.postcode, ' ', '') == normalised
        ).first()

        if pc and pc.latitude:
            logger.info(
                'GEOCODED id=%d: %s -> (%.6f, %.6f)',
                p.id, p.postcode, pc.latitude, pc.longitude,
            )
            if not dry_run:
                p.latitude = pc.latitude
                p.longitude = pc.longitude
            fixed_ids.append(p.id)

    return fixed_ids


def enrich_properties(db, property_ids: list[int]):
    """Re-enrich specific properties with neighbourhood data."""
    if not property_ids:
        return
    from backend.services.neighbourhood_service import enrich_property

    logger.info('Re-enriching %d properties...', len(property_ids))
    for pid in property_ids:
        prop = db.query(Property).get(pid)
        if prop:
            try:
                enrich_property(db, prop)
            except Exception as e:
                logger.warning('Enrich error for id=%d: %s', pid, e)

    db.commit()
    logger.info('Re-enrichment complete')


def main():
    parser = argparse.ArgumentParser(description='Clean up property postcodes and backfill coordinates')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    group.add_argument('--commit', action='store_true', help='Apply changes to database')
    parser.add_argument('--enrich', action='store_true', help='Re-enrich fixed properties (use with --commit)')
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        logger.info('=== DRY RUN — no changes will be written ===')

    db = SessionLocal()
    try:
        logger.info('Phase 1: Fixing corrupted postcodes...')
        corrupted_ids = phase1_fix_corrupted(db, dry_run)
        logger.info('Phase 1 complete: %d corrupted postcodes fixed', len(corrupted_ids))

        if not dry_run:
            db.commit()

        logger.info('Phase 2: Extracting postcodes from addresses...')
        extracted_ids = phase2_extract_from_address(db, dry_run)
        logger.info('Phase 2 complete: %d postcodes extracted from addresses', len(extracted_ids))

        if not dry_run:
            db.commit()

        logger.info('Phase 3: Backfilling coordinates...')
        geocoded_ids = phase3_backfill_coords(db, dry_run)
        logger.info('Phase 3 complete: %d coordinates backfilled', len(geocoded_ids))

        if not dry_run:
            db.commit()

        all_fixed = list(set(corrupted_ids + extracted_ids + geocoded_ids))

        logger.info('=== SUMMARY ===')
        logger.info('Corrupted postcodes fixed:  %d', len(corrupted_ids))
        logger.info('Postcodes extracted:        %d', len(extracted_ids))
        logger.info('Coordinates backfilled:     %d', len(geocoded_ids))
        logger.info('Total properties affected:  %d', len(all_fixed))

        if args.enrich and not dry_run and all_fixed:
            enrich_properties(db, all_fixed)

    finally:
        db.close()


if __name__ == '__main__':
    main()
