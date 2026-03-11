"""
Backfill latitude/longitude for all existing properties missing coordinates.

Run once after applying migration 015:
    python scripts/backfill_coordinates.py

Geocodes via postcodes.io (free, no API key). Respects a short delay between
requests to avoid hammering the API.
"""
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.models.base import SessionLocal
from backend.models.property import Property
from backend.services.geocoder import geocode_postcode

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BATCH_SIZE = 100
DELAY_SECS = 0.1  # 100ms between postcodes.io calls


def main():
    db = SessionLocal()
    try:
        total = (
            db.query(Property)
            .filter(Property.latitude.is_(None), Property.postcode.isnot(None))
            .count()
        )
        logger.info("Properties needing geocoding: %d", total)

        processed = 0
        updated = 0
        failed = 0

        while True:
            props = (
                db.query(Property)
                .filter(Property.latitude.is_(None), Property.postcode.isnot(None))
                .limit(BATCH_SIZE)
                .all()
            )
            if not props:
                break

            for prop in props:
                coords = geocode_postcode(prop.postcode)
                if coords:
                    prop.latitude, prop.longitude = coords
                    updated += 1
                else:
                    failed += 1
                processed += 1
                if processed % 50 == 0:
                    logger.info("Progress: %d/%d (updated=%d, failed=%d)", processed, total, updated, failed)
                time.sleep(DELAY_SECS)

            db.commit()

        logger.info(
            "Done: %d processed, %d geocoded, %d failed",
            processed, updated, failed,
        )
    finally:
        db.close()


if __name__ == '__main__':
    main()
