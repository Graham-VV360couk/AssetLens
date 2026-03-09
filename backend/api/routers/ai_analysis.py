"""AI property analysis endpoints."""
import logging
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


def _run_batch(limit: int):
    from backend.models.base import SessionLocal
    db = SessionLocal()
    try:
        # Get properties without an AI insight, ordered by score desc
        analysed_ids = db.query(PropertyAIInsight.property_id).subquery()
        props = (
            db.query(Property)
            .filter(Property.status == 'active')
            .filter(Property.id.notin_(analysed_ids))
            .join(Property.score, isouter=True)
            .order_by(Property.score.has() and Property.score.investment_score.desc())
            .limit(limit)
            .all()
        )
        logger.info("AI batch: analysing %d properties", len(props))
        for prop in props:
            try:
                analyse_property(prop.id, db)
            except Exception as e:
                logger.warning("AI batch: property %d failed: %s", prop.id, e)
    finally:
        db.close()


@router.post('/analyse/batch')
def analyse_batch(background_tasks: BackgroundTasks, limit: int = 50):
    """Queue background AI analysis for up to `limit` unanalysed properties."""
    background_tasks.add_task(_run_batch, limit)
    return {"message": f"AI batch analysis started for up to {limit} properties"}


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
