"""Property scoring endpoints — trigger scoring job and LR data import."""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.models.base import SessionLocal
from backend.models.property import Property, PropertyScore
from backend.services.scoring_service import PropertyScoringService, save_score
from backend.services.propertydata_service import get_service as get_pd_service

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
                    existing_score = db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()
                    result = scorer.score_property(prop, existing_score=existing_score)
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


def _run_enrichment_job(min_score: float = 60.0, limit: int = 50):
    """Enrich properties with PropertyData.co.uk AVM and rental data.

    Only enriches properties that:
    - Have an investment score >= min_score (selective to save credits)
    - Have not been enriched yet (pd_enriched_at is NULL)
    """
    db = SessionLocal()
    pd = get_pd_service()
    try:
        candidates = (
            db.query(Property, PropertyScore)
            .join(PropertyScore, PropertyScore.property_id == Property.id)
            .filter(
                Property.status == 'active',
                PropertyScore.investment_score >= min_score,
                PropertyScore.pd_enriched_at.is_(None),
            )
            .order_by(PropertyScore.investment_score.desc())
            .limit(limit)
            .all()
        )
        logger.info("Enriching %d properties with PropertyData...", len(candidates))
        scorer = PropertyScoringService(db)
        enriched = 0
        errors = 0

        for prop, score in candidates:
            try:
                ok = pd.enrich(prop, score, db)
                if ok:
                    # Re-score using the new PD values
                    result = scorer.score_property(prop, existing_score=score)
                    save_score(db, prop, result)
                    enriched += 1
            except Exception as e:
                logger.warning("Enrichment failed for property %d: %s", prop.id, e)
                errors += 1

        logger.info("Enrichment complete: %d enriched, %d errors", enriched, errors)
    except Exception as e:
        logger.error("Enrichment job failed: %s", e)
    finally:
        db.close()


@router.post('/run')
def trigger_scoring(background_tasks: BackgroundTasks):
    """Trigger scoring for all active properties."""
    background_tasks.add_task(_run_scoring_job)
    return {"message": "Scoring job started for all active properties"}


@router.post('/enrich')
def trigger_enrichment(
    background_tasks: BackgroundTasks,
    min_score: float = 60.0,
    limit: int = 50,
):
    """Enrich top-scoring properties with PropertyData AVM + rental estimates.

    Uses ~3 API credits per property (AVM + rental + flood risk).
    Only enriches un-enriched properties above min_score to conserve credits.
    """
    background_tasks.add_task(_run_enrichment_job, min_score=min_score, limit=limit)
    return {
        "message": f"Enrichment job started (min_score={min_score}, limit={limit})",
        "estimated_credits": limit * 3,
    }


@router.post('/enrich/{property_id}')
def enrich_property(property_id: int, db: Session = Depends(get_db)):
    """Enrich a single property with PropertyData AVM + rental + flood risk (3 credits)."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    score = db.query(PropertyScore).filter(PropertyScore.property_id == property_id).first()
    if not score:
        score = PropertyScore(property_id=property_id)
        db.add(score)
        db.flush()

    pd = get_pd_service()
    ok = pd.enrich(prop, score, db)
    if not ok:
        raise HTTPException(status_code=503, detail="PropertyData enrichment failed — check API key or quota")

    scorer = PropertyScoringService(db)
    result = scorer.score_property(prop, existing_score=score)
    save_score(db, prop, result)
    db.commit()
    db.refresh(score)

    return {
        "pd_avm": score.pd_avm,
        "pd_avm_lower": score.pd_avm_lower,
        "pd_avm_upper": score.pd_avm_upper,
        "pd_rental_estimate": score.pd_rental_estimate,
        "pd_flood_risk": score.pd_flood_risk,
        "pd_enriched_at": score.pd_enriched_at.isoformat() if score.pd_enriched_at else None,
        "investment_score": score.investment_score,
    }


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
