"""Async enrichment task — triggered by upload endpoints."""
import logging

from backend.celery_app import celery_app
from backend.models.base import SessionLocal
from backend.models.property import Property, PropertyScore
from backend.services.propertydata_service import PropertyDataService
from backend.services.ai_analysis_service import analyse_property

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_property_task(self, property_id: int):
    """
    Enrich a single property with PropertyData + AI analysis.
    Called via .delay(property_id) from upload handlers.
    """
    db = SessionLocal()
    try:
        prop = db.query(Property).get(property_id)
        if not prop:
            logger.warning("Enrichment: property %d not found", property_id)
            return

        score = db.query(PropertyScore).filter(PropertyScore.property_id == property_id).first()
        if not score:
            score = PropertyScore(property_id=property_id)
            db.add(score)
            db.flush()

        pd_service = PropertyDataService()
        try:
            pd_service.enrich(prop, score, db)
        except Exception as e:
            logger.warning("PD enrichment failed for %d: %s", property_id, e)

        try:
            analyse_property(property_id, db)
        except Exception as e:
            logger.warning("AI analysis failed for %d: %s", property_id, e)

        db.commit()
        logger.info("Enrichment complete for property %d", property_id)
    except Exception as e:
        logger.error("Enrichment task failed for %d: %s", property_id, e)
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
