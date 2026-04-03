"""Neighbourhood report API endpoint."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.api.schemas import NeighbourhoodReport
from backend.services.neighbourhood_report import generate_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/neighbourhood', tags=['neighbourhood'])


@router.get('/{postcode}', response_model=NeighbourhoodReport)
def get_neighbourhood_report(
    postcode: str,
    db: Session = Depends(get_db),
):
    """
    Generate a full neighbourhood intelligence report for any UK postcode.

    Returns schools, crime stats, broadband, transport, planning constraints,
    sales history, and nearby properties for sale.

    Works for ANY UK postcode — not just properties in our database.
    """
    postcode = postcode.strip().upper()
    if not postcode:
        raise HTTPException(status_code=400, detail='Postcode is required')

    report = generate_report(db, postcode)

    if 'error' in report:
        raise HTTPException(status_code=404, detail=report['error'])

    return report
