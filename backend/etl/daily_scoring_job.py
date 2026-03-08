"""
Daily Scoring ETL Job (Task #14)
Runs nightly to score all active properties.
"""
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.property import Property, PropertyScore
from backend.services.scoring_service import PropertyScoringService, save_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BATCH_SIZE = 500
HIGH_SCORE_THRESHOLD = 70.0


def run_scoring_job():
    db = SessionLocal()
    try:
        total = db.query(Property).filter(Property.status == 'active').count()
        logger.info("Scoring %d active properties...", total)

        scorer = PropertyScoringService(db)
        stats = {'scored': 0, 'high_value': 0, 'errors': 0}
        offset = 0

        while True:
            batch = (
                db.query(Property)
                .filter(Property.status == 'active')
                .order_by(Property.id)
                .offset(offset)
                .limit(BATCH_SIZE)
                .all()
            )
            if not batch:
                break

            for prop in batch:
                try:
                    result = scorer.score_property(prop)
                    save_score(db, prop, result)
                    stats['scored'] += 1
                    if result.investment_score >= HIGH_SCORE_THRESHOLD:
                        stats['high_value'] += 1
                except Exception as e:
                    logger.warning("Error scoring property %d: %s", prop.id, e)
                    stats['errors'] += 1

            db.commit()
            offset += BATCH_SIZE
            logger.info("Progress: %d/%d (%.1f%%)", offset, total, min(100, offset / total * 100))

        logger.info("Scoring complete: %s", stats)
        return stats

    finally:
        db.close()


if __name__ == '__main__':
    run_scoring_job()
