"""
PropertyData.co.uk enrichment service.

Calls up to 3 endpoints per property (AVM, rental-valuation, flood-risk).
Each call costs 1 API credit; a full enrichment = 3 credits.

Enriched values are written to property_scores and used by scoring_service
in place of the statistical fallbacks.
"""
import logging
import os
import time
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from backend.models.property import Property, PropertyScore

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("PROPERTYDATA_API_KEY", "")
_BASE = "https://api.propertydata.co.uk"
# Delay between individual endpoint calls within one property enrichment (3 calls)
_PD_CALL_DELAY = float(os.getenv("PD_CALL_DELAY", "0.5"))

# Map our property types to PropertyData codes
_TYPE_MAP = {
    "detached": "D",
    "semi-detached": "SD",
    "terraced": "T",
    "flat": "F",
    "apartment": "F",
    "maisonette": "F",
    "bungalow": "D",
    "end-terrace": "T",
    "end terrace": "T",
}


def _pd_type(prop_type: Optional[str]) -> str:
    if not prop_type:
        return "T"
    return _TYPE_MAP.get(prop_type.lower().strip(), "T")


class PropertyDataService:
    """Enrich a property record using PropertyData.co.uk API."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or _API_KEY
        self.client = httpx.Client(timeout=15.0)

    def enrich(self, prop: Property, score: PropertyScore, db: Session) -> bool:
        """
        Fetch AVM, rental estimate and flood risk from PropertyData.
        Updates score in-place and commits.  Returns True on success.
        """
        if not self.api_key:
            logger.warning("PROPERTYDATA_API_KEY not set — skipping enrichment")
            return False

        postcode = (prop.postcode or "").replace(" ", "")
        pd_type = _pd_type(prop.property_type)
        beds = prop.bedrooms or 3

        success = False

        # --- AVM ---
        avm = self._avm(postcode, pd_type, beds)
        if avm:
            score.pd_avm = avm.get("estimate")
            score.pd_avm_lower = avm.get("range_lower")
            score.pd_avm_upper = avm.get("range_upper")
            success = True
        if _PD_CALL_DELAY > 0:
            time.sleep(_PD_CALL_DELAY)

        # --- Rental estimate ---
        rental = self._rental(postcode, pd_type, beds)
        if rental:
            score.pd_rental_estimate = rental.get("rental_estimate")
            success = True
        if _PD_CALL_DELAY > 0:
            time.sleep(_PD_CALL_DELAY)

        # --- Flood risk ---
        flood = self._flood_risk(postcode)
        if flood:
            score.pd_flood_risk = flood.get("risk_level", "").lower()
            success = True

        if success:
            score.pd_enriched_at = datetime.utcnow()
            db.commit()
            logger.info(
                "PropertyData enrichment complete for property %s: avm=%s rent=%s flood=%s",
                prop.id,
                score.pd_avm,
                score.pd_rental_estimate,
                score.pd_flood_risk,
            )

        return success

    def _call(self, endpoint: str, params: dict) -> Optional[dict]:
        """Make one PropertyData API call with 429 back-off."""
        for attempt in range(3):
            try:
                r = self.client.get(f"{_BASE}/{endpoint}", params=params)
                if r.status_code == 429:
                    wait = 30 * (attempt + 1)
                    logger.warning("PropertyData 429 on /%s — waiting %ds", endpoint, wait)
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                body = r.json()
                if body.get("status") == "success":
                    return body.get("data", {})
                logger.debug("PropertyData /%s non-success: %s", endpoint, body.get("message"))
                return None
            except Exception as exc:
                logger.warning("PropertyData /%s failed (attempt %d): %s", endpoint, attempt + 1, exc)
                if attempt < 2:
                    time.sleep(5)
        return None

    def _avm(self, postcode: str, pd_type: str, beds: int) -> Optional[dict]:
        return self._call("avm", {"key": self.api_key, "postcode": postcode,
                                  "property_type": pd_type, "bedrooms": beds})

    def _rental(self, postcode: str, pd_type: str, beds: int) -> Optional[dict]:
        return self._call("rental-valuation", {"key": self.api_key, "postcode": postcode,
                                               "property_type": pd_type, "bedrooms": beds})

    def _flood_risk(self, postcode: str) -> Optional[dict]:
        return self._call("flood-risk", {"key": self.api_key, "postcode": postcode})

    def close(self):
        self.client.close()


_service: Optional[PropertyDataService] = None


def get_service() -> PropertyDataService:
    global _service
    if _service is None:
        _service = PropertyDataService()
    return _service
