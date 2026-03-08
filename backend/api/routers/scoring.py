"""Property scoring endpoints — trigger scoring job and LR data import."""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.models.base import SessionLocal
from backend.models.property import Property, PropertyScore
from backend.services.scoring_service import PropertyScoringService, save_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/scoring', tags=['scoring'])

BATCH_SIZE = 100


def _run_scoring_job(property_ids: list = None):
    """Score all active properties (or a specific subset by ID list)."""
    db = SessionLocal()
    try:
        q = db.query(Property).filter(Property.status == 'active')
        if property_ids:
            q = q.filter(Property.id.in_(property_ids))
        total = q.count()
        logger.info("Scoring %d properties...", total)

        scorer = PropertyScoringService(db)
        scored = 0
        errors = 0
        offset = 0

        while True:
            batch = q.order_by(Property.id).offset(offset).limit(BATCH_SIZE).all()
            if not batch:
                break
            for prop in batch:
                try:
                    result = scorer.score_property(prop)
                    save_score(db, prop, result)
                    scored += 1
                except Exception as e:
                    logger.warning("Error scoring property %d: %s", prop.id, e)
                    errors += 1
            db.commit()
            offset += BATCH_SIZE

        logger.info("Scoring complete: %d scored, %d errors", scored, errors)
    except Exception as e:
        logger.error("Scoring job failed: %s", e)
    finally:
        db.close()


@router.post('/run')
def trigger_scoring(background_tasks: BackgroundTasks):
    """Trigger scoring for all active properties."""
    background_tasks.add_task(_run_scoring_job)
    return {"message": "Scoring job started for all active properties"}


@router.get('/status')
def scoring_status(db: Session = Depends(get_db)):
    """Return scoring coverage stats."""
    total_active = db.query(Property).filter(Property.status == 'active').count()
    total_scored = db.query(PropertyScore).count()
    last_score = db.query(PropertyScore).order_by(PropertyScore.calculated_at.desc()).first()
    return {
        "total_active": total_active,
        "total_scored": total_scored,
        "unscored": total_active - total_scored,
        "last_calculated_at": last_score.calculated_at.isoformat() if last_score else None,
    }
