"""Neighbourhood report API endpoint."""
import json
import logging
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.services.neighbourhood_report import generate_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/neighbourhood', tags=['neighbourhood'])


class SafeEncoder(json.JSONEncoder):
    """Handle date, datetime, Decimal and other non-serialisable types."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        return super().default(obj)


@router.get('/{postcode}')
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

    # Use safe encoder to handle dates, Decimals, etc.
    content = json.loads(json.dumps(report, cls=SafeEncoder))
    return JSONResponse(content=content)
