"""
Daily Alert Email Job (Task #19)
Queries high-investment-score properties and sends daily digest email.
Scheduled at 6 AM UTC.
"""
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from backend.models.base import SessionLocal
from backend.models.property import Property, PropertyScore
from backend.services.email_service import EmailAlertService

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HIGH_SCORE_THRESHOLD = float(os.environ.get('ALERT_SCORE_THRESHOLD', '70'))


def run_alert_job():
    db = SessionLocal()
    try:
        # Query high-value properties not yet reviewed
        high_value = (
            db.query(Property)
            .join(PropertyScore, Property.id == PropertyScore.property_id)
            .options(joinedload(Property.score))
            .filter(
                Property.status == 'active',
                PropertyScore.investment_score >= HIGH_SCORE_THRESHOLD,
            )
            .order_by(PropertyScore.investment_score.desc())
            .limit(50)
            .all()
        )

        if not high_value:
            logger.info("No high-value properties found (threshold=%.0f)", HIGH_SCORE_THRESHOLD)
            return

        # Compute stats
        scores = [p.score.investment_score for p in high_value if p.score and p.score.investment_score]
        avg_score = round(sum(scores) / len(scores)) if scores else 0
        brilliant = sum(1 for p in high_value if p.score and p.score.price_band == 'brilliant')

        # Total high-value across all properties
        total_hv = (
            db.query(func.count(PropertyScore.id))
            .filter(PropertyScore.investment_score >= HIGH_SCORE_THRESHOLD)
            .scalar()
        ) or 0

        stats = {
            'total_high_value': total_hv,
            'brilliant_count': brilliant,
            'avg_score': avg_score,
        }

        logger.info("Sending alert: %d properties, avg score=%d", len(high_value), avg_score)

        # Convert to dicts for template
        prop_dicts = []
        for p in high_value:
            d = {
                'address': p.address,
                'postcode': p.postcode,
                'town': p.town,
                'asking_price': p.asking_price,
                'bedrooms': p.bedrooms,
                'score': None,
            }
            if p.score:
                d['score'] = {
                    'investment_score': p.score.investment_score,
                    'gross_yield_pct': p.score.gross_yield_pct,
                    'price_deviation_pct': p.score.price_deviation_pct,
                    'estimated_value': p.score.estimated_value,
                    'price_band': p.score.price_band,
                }
            prop_dicts.append(d)

        email_svc = EmailAlertService()
        sent = email_svc.send_daily_digest(prop_dicts, stats)
        logger.info("Email %s", "sent" if sent else "skipped (not configured)")

        return {'sent': sent, 'properties': len(high_value), 'stats': stats}

    finally:
        db.close()


if __name__ == '__main__':
    result = run_alert_job()
    logger.info("Alert job complete: %s", result)
