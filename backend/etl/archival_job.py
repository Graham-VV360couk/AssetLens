"""
Property Archival System (Task #20)
Archives stale properties and handles 6-month re-check suppression.
Scheduled weekly.
"""
import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy.orm import Session

from backend.models.base import SessionLocal
from backend.models.property import Property, PropertySource

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ARCHIVE_AFTER_DAYS = int(os.environ.get('ARCHIVE_AFTER_DAYS', '180'))  # 6 months
SUPPRESS_DAYS = int(os.environ.get('SUPPRESS_DAYS', '180'))  # 6-month re-check


class ArchivalJob:
    def __init__(self, db: Session, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.stats = {'archived': 0, 'restored': 0, 'suppressed': 0, 'errors': 0}

    def run(self):
        logger.info("Starting archival job (dry_run=%s)", self.dry_run)
        self._archive_stale_properties()
        self._archive_reviewed_suppressed()
        self._restore_relisted_properties()
        logger.info("Archival complete: %s", self.stats)
        return self.stats

    def _archive_stale_properties(self):
        """Archive active properties not seen since ARCHIVE_AFTER_DAYS."""
        cutoff = datetime.utcnow() - timedelta(days=ARCHIVE_AFTER_DAYS)

        # Find active properties where all sources have been inactive since cutoff
        stale = (
            self.db.query(Property)
            .filter(Property.status == 'active')
            .filter(Property.date_found <= cutoff)
            .filter(~Property.is_reviewed)
            .all()
        )

        for prop in stale:
            # Check if any source is still active recently
            active_source = (
                self.db.query(PropertySource)
                .filter(
                    PropertySource.property_id == prop.id,
                    PropertySource.is_active == True,
                    PropertySource.last_seen_at >= cutoff,
                )
                .first()
            )

            if not active_source:
                logger.info("Archiving stale property %d: %s", prop.id, prop.address[:50])
                if not self.dry_run:
                    prop.status = 'archived'
                self.stats['archived'] += 1

        if not self.dry_run:
            self.db.commit()

    def _archive_reviewed_suppressed(self):
        """Archive properties reviewed >6 months ago (re-check suppression)."""
        cutoff = datetime.utcnow() - timedelta(days=SUPPRESS_DAYS)

        suppressed = (
            self.db.query(Property)
            .filter(
                Property.status == 'active',
                Property.is_reviewed == True,
                Property.reviewed_at <= cutoff,
            )
            .all()
        )

        for prop in suppressed:
            logger.info("Suppressing reviewed property %d: %s", prop.id, prop.address[:50])
            if not self.dry_run:
                prop.status = 'suppressed'
            self.stats['suppressed'] += 1

        if not self.dry_run:
            self.db.commit()

    def _restore_relisted_properties(self):
        """Restore archived/suppressed properties that have been seen recently."""
        recent = datetime.utcnow() - timedelta(days=30)

        relisted = (
            self.db.query(Property)
            .join(PropertySource, Property.id == PropertySource.property_id)
            .filter(
                Property.status.in_(['archived', 'suppressed']),
                PropertySource.is_active == True,
                PropertySource.last_seen_at >= recent,
            )
            .distinct()
            .all()
        )

        for prop in relisted:
            logger.info("Restoring re-listed property %d: %s", prop.id, prop.address[:50])
            if not self.dry_run:
                prop.status = 'active'
                prop.is_reviewed = False  # Reset review on re-list
            self.stats['restored'] += 1

        if not self.dry_run:
            self.db.commit()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Property archival job')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        job = ArchivalJob(db, dry_run=args.dry_run)
        job.run()
    finally:
        db.close()


if __name__ == '__main__':
    main()
