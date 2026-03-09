"""AI property analysis endpoints."""
import logging
import time
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.models.property import Property
from backend.models.property_ai_insight import PropertyAIInsight
from backend.services.ai_analysis_service import analyse_property

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/ai', tags=['ai'])


class InsightResponse(BaseModel):
    property_id: int
    verdict: str
    confidence: Optional[float]
    summary: Optional[str]
    location_notes: Optional[str]
    positives: Optional[List[str]]
    risks: Optional[List[str]]
    tokens_used: Optional[int]
    generated_at: Optional[str]

    model_config = {'from_attributes': True}


@router.post('/analyse/property/{property_id}')
def analyse_one(property_id: int, db: Session = Depends(get_db)):
    """Analyse a single property with Claude. Synchronous — waits for result."""
    try:
        result = analyse_property(property_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("AI analysis failed for property %d: %s", property_id, e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


def _run_batch(limit: int, min_score: float = 60.0):
    """Background task: analyse up to `limit` unanalysed properties in score order.

    Calls are paced by AI_CALL_DELAY (default 2s) via the service layer.
    Stops early if it receives consecutive 429/rate-limit errors.
    """
    from backend.models.base import SessionLocal
    from backend.models.property import PropertyScore
    db = SessionLocal()
    consecutive_errors = 0
    analysed = 0
    try:
        analysed_ids = db.query(PropertyAIInsight.property_id).subquery()
        props = (
            db.query(Property)
            .join(PropertyScore, PropertyScore.property_id == Property.id)
            .filter(
                Property.status == 'active',
                PropertyScore.investment_score >= min_score,
                Property.id.notin_(analysed_ids),
            )
            .order_by(PropertyScore.investment_score.desc())
            .limit(limit)
            .all()
        )
        logger.info("AI batch: analysing %d properties (min_score=%.0f)", len(props), min_score)
        for prop in props:
            try:
                # _rate_limit_delay=False: batch manages its own pacing via sleep below
                analyse_property(prop.id, db, _rate_limit_delay=False)
                analysed += 1
                consecutive_errors = 0
                # Pace between calls — prevents 429 on lower API tiers
                from backend.services.ai_analysis_service import AI_CALL_DELAY
                if AI_CALL_DELAY > 0:
                    time.sleep(AI_CALL_DELAY)
            except Exception as e:
                consecutive_errors += 1
                logger.warning("AI batch: property %d failed: %s", prop.id, e)
                if consecutive_errors >= 3:
                    logger.error("AI batch: 3 consecutive errors — stopping to avoid further throttling")
                    break
                # Back off on rate limit errors
                if 'rate' in str(e).lower() or '429' in str(e):
                    logger.warning("AI batch: rate limit hit — sleeping 60s")
                    time.sleep(60)
        logger.info("AI batch complete: %d analysed", analysed)
    finally:
        db.close()


@router.post('/analyse/batch')
def analyse_batch(
    background_tasks: BackgroundTasks,
    limit: int = 20,
    min_score: float = 60.0,
):
    """Queue background AI analysis for up to `limit` unanalysed properties.

    Properties are processed highest-score-first.
    Default limit reduced to 20 to stay within API rate limits.
    Increase AI_CALL_DELAY env var if you hit throttling (default: 2s between calls).
    """
    background_tasks.add_task(_run_batch, limit, min_score)
    return {
        "message": f"AI batch started: up to {limit} properties (score ≥ {min_score:.0f})",
        "estimated_duration_seconds": limit * 3,
    }


@router.get('/insights/{property_id}', response_model=InsightResponse)
def get_insight(property_id: int, db: Session = Depends(get_db)):
    """Retrieve stored AI insight for a property."""
    import json
    insight = db.query(PropertyAIInsight).filter(PropertyAIInsight.property_id == property_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="No AI analysis yet for this property")
    return {
        'property_id': insight.property_id,
        'verdict': insight.verdict,
        'confidence': insight.confidence,
        'summary': insight.summary,
        'location_notes': insight.location_notes,
        'positives': json.loads(insight.positives or '[]'),
        'risks': json.loads(insight.risks or '[]'),
        'tokens_used': insight.tokens_used,
        'generated_at': insight.generated_at.isoformat() if insight.generated_at else None,
    }


@router.get('/status')
def ai_status(db: Session = Depends(get_db)):
    total_active = db.query(Property).filter(Property.status == 'active').count()
    total_analysed = db.query(PropertyAIInsight).count()
    return {
        'total_active': total_active,
        'total_analysed': total_analysed,
        'unanalysed': total_active - total_analysed,
    }
