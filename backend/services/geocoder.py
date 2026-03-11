"""
Geocoder service — postcodes.io wrapper.

Uses the free postcodes.io API (no key required) to convert UK postcodes to
(latitude, longitude). Results are cached in-process with functools.lru_cache
to avoid repeated API calls for the same postcode.
"""
import functools
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)
POSTCODES_IO = "https://api.postcodes.io/postcodes/{}"


@functools.lru_cache(maxsize=4096)
def geocode_postcode(postcode: str) -> Optional[tuple]:
    """
    Return (latitude, longitude) for a UK postcode via postcodes.io.

    Args:
        postcode: UK postcode string (any formatting — normalised internally).

    Returns:
        (lat, lon) tuple of floats, or None if not found / API error.
    """
    clean = postcode.strip().upper().replace(" ", "")
    if not clean:
        return None
    try:
        resp = requests.get(POSTCODES_IO.format(clean), timeout=5)
        if resp.status_code == 200:
            result = resp.json().get("result") or {}
            if result.get("latitude") and result.get("longitude"):
                return float(result["latitude"]), float(result["longitude"])
        elif resp.status_code == 404:
            logger.debug("postcodes.io: no result for %s", clean)
        else:
            logger.warning("postcodes.io returned %s for %s", resp.status_code, clean)
    except Exception as e:
        logger.warning("geocode_postcode(%s) failed: %s", clean, e)
    return None
