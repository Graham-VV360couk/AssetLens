"""On-demand property scan endpoint."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.auth.guards import require_subscription
from backend.models.user import User
from backend.services.scan_service import ScanService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scan", tags=["scan"])


class ScanRequest(BaseModel):
    address: Optional[str] = Field(None, description="Property address (optional for area scan)")
    postcode: str = Field(..., description="UK postcode (required)")


@router.post("")
def scan_property(
    req: ScanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_subscription('investor', 'admin', trial_type='property_view')),
):
    """
    Scan any UK property by address + postcode.
    Returns full intelligence profile (or area-level data if postcode only).
    """
    if user.subscription_status == 'trial':
        user.trial_property_views += 1
        db.commit()
    try:
        svc = ScanService(db)
        result = svc.scan(address=req.address or '', postcode=req.postcode)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Scan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Scan failed")
