"""
Stale Listing Checker ETL Job
Re-checks active/STC properties that haven't been seen in the feed for 7+ days.
Catches properties that went sold outside the incremental feed window.
Runs weekly on Wednesdays via run_etl.sh.
"""
import logging
import os
import sys
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.property import Property, PropertySource
from backend.models.sales_history import SalesHistory
from backend.services.searchland_client import SearchlandClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

STALE_AFTER_DAYS = 7


class StaleListingChecker:
    def __init__(self, db: Session):
        self.db = db
        self._client = None  # Lazily initialized to allow testing without API key
        self.stats = {'rechecked': 0, 'sold': 0, 'stc': 0, 'still_active': 0, 'errors': 0}

    @property
    def client(self):
        if self._client is None:
            self._client = SearchlandClient()
        return self._client

    def run(self):
        cutoff = datetime.utcnow() - timedelta(days=STALE_AFTER_DAYS)
        stale = (
            self.db.query(Property)
            .join(PropertySource, Property.id == PropertySource.property_id)
            .filter(
                Property.status.in_(['active', 'stc']),
                PropertySource.is_active == True,
                PropertySource.last_seen_at < cutoff,
            )
            .all()
        )
        logger.info("Found %d stale properties to recheck", len(stale))

        for prop in stale:
            try:
                outcome = self._recheck_property(prop)
                self.stats['rechecked'] += 1
                if outcome == 'sold':
                    self.stats['sold'] += 1
                elif outcome == 'stc':
                    self.stats['stc'] += 1
                else:
                    self.stats['still_active'] += 1
            except Exception as e:
                logger.warning("Recheck failed for property %d: %s", prop.id, e)
                self.stats['errors'] += 1

        self.db.commit()
        logger.info("Stale check complete: %s", self.stats)
        return self.stats

    def _recheck_property(self, prop: Property) -> str:
        """Fetch current status from PropertyData by source_id. Returns 'active', 'stc', or 'sold'."""
        source = next(
            (s for s in prop.sources if s.source_name in ('searchland', 'propertydata') and s.source_id),
            None,
        )
        if not source:
            return 'active'

        try:
            fresh = self.client.get_property_by_id(source.source_id)
        except Exception:
            return 'active'  # Can't reach API — assume still active, retry next week

        if fresh is None:
            # Not found in API (404) — possibly delisted; treat as sold without price
            self._apply_sold(prop, sold_price=None)
            return 'sold'

        raw_status = (fresh.get('status') or '').lower()
        mapped = self.client._STATUS_MAP.get(raw_status, 'active')

        if mapped == 'sold':
            self._apply_sold(prop, sold_price=fresh.get('sold_price'))
            return 'sold'
        elif mapped == 'stc':
            self._apply_stc(prop)
            return 'stc'
        else:
            # Still active — update last_seen_at
            source.last_seen_at = datetime.utcnow()
            return 'active'

    def _apply_sold(self, prop: Property, sold_price):
        prop.status = 'sold'
        prop.date_sold = date.today()
        self.db.add(SalesHistory(
            property_id=prop.id,
            address=prop.address,
            postcode=prop.postcode,
            sale_date=date.today(),
            sale_price=sold_price,
            property_type=prop.property_type or 'unknown',
        ))

    def _apply_stc(self, prop: Property):
        prop.status = 'stc'


def main():
    db = SessionLocal()
    try:
        checker = StaleListingChecker(db)
        checker.run()
    finally:
        db.close()


if __name__ == '__main__':
    main()
