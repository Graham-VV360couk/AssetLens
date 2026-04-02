"""
Licensed Feed Daily Import ETL Job (Task #8)
Pulls property listings from Searchland/PropertyData API and merges into database.
Scheduled daily at 2 AM UTC.
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.property import Property, PropertySource
from backend.models.sales_history import SalesHistory
from backend.services.searchland_client import SearchlandClient
from backend.services.deduplication_service import PropertyDeduplicator

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


class LicensedFeedImporter:
    def __init__(self, db: Session, incremental: bool = True):
        self.db = db
        self.incremental = incremental
        self.client = SearchlandClient()
        self.deduplicator = PropertyDeduplicator(db)
        self.stats = {
            'fetched': 0,
            'new': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
        }

    def run(self, postcodes: Optional[list] = None, property_type: Optional[str] = None):
        logger.info("Starting licensed feed import (incremental=%s)", self.incremental)
        start = datetime.utcnow()

        updated_since = None
        if self.incremental:
            # Find last import time
            last_source = (
                self.db.query(PropertySource)
                .filter(PropertySource.source_name.in_(['searchland', 'propertydata']))
                .order_by(PropertySource.imported_at.desc())
                .first()
            )
            if last_source:
                updated_since = last_source.imported_at - timedelta(hours=1)  # overlap
                logger.info("Incremental sync from %s", updated_since)

        params = {}
        if postcodes:
            params['postcodes'] = postcodes
        if property_type:
            params['property_type'] = property_type
        if updated_since:
            params['updated_since'] = updated_since.isoformat()

        try:
            properties = self.client.fetch_all_properties(**params)
            logger.info("Fetched %d properties from API", len(properties))
            self.stats['fetched'] = len(properties)

            for raw in properties:
                try:
                    self._process_property(raw)
                except Exception as e:
                    logger.warning("Error processing property: %s", e)
                    self.stats['errors'] += 1

            self.db.commit()

        except Exception as e:
            logger.error("Feed import failed: %s", e)
            self.db.rollback()
            raise

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Import complete in %.1fs: fetched=%d new=%d updated=%d errors=%d",
            elapsed,
            self.stats['fetched'],
            self.stats['new'],
            self.stats['updated'],
            self.stats['errors'],
        )
        return self.stats

    def _process_property(self, raw: dict):
        normalized = self.client.normalize_property_data(raw)
        incoming_status = normalized.get('status', 'active')
        sold_price = normalized.get('sold_price')
        duplicate = self.deduplicator.find_duplicate(
            address=normalized.get('address', ''),
            postcode=normalized.get('postcode', ''),
        )

        if duplicate:
            self.deduplicator.merge_property_data(
                duplicate,
                normalized,
                source_name=normalized.get('source_name', 'searchland'),
                source_id=str(normalized.get('source_id', '')),
                source_url=normalized.get('source_url', ''),
            )
            # Backfill coordinates if missing
            if duplicate.latitude is None and duplicate.postcode:
                self._geocode_property(duplicate)
            self._apply_status_change(duplicate, incoming_status, sold_price)
            self.stats['updated'] += 1
        else:
            prop = Property(
                address=normalized.get('address', ''),
                postcode=normalized.get('postcode', ''),
                town=normalized.get('town', ''),
                county=normalized.get('county', ''),
                property_type=normalized.get('property_type', 'unknown'),
                bedrooms=normalized.get('bedrooms'),
                bathrooms=normalized.get('bathrooms'),
                asking_price=normalized.get('asking_price'),
                status='active',  # may be updated below by _apply_status_change
                date_found=datetime.utcnow(),
                description=normalized.get('description', ''),
                image_url=normalized.get('image_url'),
                image_urls=normalized.get('image_urls'),
            )
            self.db.add(prop)
            self.db.flush()
            self.deduplicator.add_property_source(
                prop.id,
                source_name=normalized.get('source', 'searchland'),
                source_id=str(normalized.get('source_id', '')),
                source_url=normalized.get('source_url', ''),
            )
            # Geocode on first import
            if prop.postcode:
                self._geocode_property(prop)
            self._apply_status_change(prop, incoming_status, sold_price)
            self.stats['new'] += 1

    def _geocode_property(self, prop: Property):
        """Geocode a property's postcode and store lat/lon. Silently skips on error."""
        try:
            from backend.services.geocoder import geocode_postcode
            coords = geocode_postcode(prop.postcode)
            if coords:
                prop.latitude, prop.longitude = coords
        except Exception as e:
            logger.debug("Geocode failed for postcode %s: %s", prop.postcode, e)

    def _apply_status_change(self, prop: Property, new_status: str, sold_price):
        """
        Update property status based on feed signal.
        - 'stc'  → mark STC, property stays visible
        - 'sold' → write SalesHistory, archive property
        - 'active' → no change
        """
        if new_status == 'stc':
            prop.status = 'stc'
        elif new_status == 'sold':
            prop.status = 'sold'
            prop.date_sold = datetime.utcnow().date()
            self.db.add(SalesHistory(
                property_id=prop.id,
                address=prop.address,
                postcode=prop.postcode,
                sale_date=datetime.utcnow().date(),
                sale_price=sold_price,
                property_type=prop.property_type,
            ))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Import licensed property feed')
    parser.add_argument('--full', action='store_true', help='Full sync (ignore last import date)')
    parser.add_argument('--postcode', nargs='+', help='Limit to specific postcodes')
    parser.add_argument('--type', dest='property_type', help='Property type filter')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        importer = LicensedFeedImporter(db, incremental=not args.full)
        importer.run(postcodes=args.postcode, property_type=args.property_type)
    finally:
        db.close()


if __name__ == '__main__':
    main()
