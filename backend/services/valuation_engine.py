"""
Property Valuation Engine

Calculates an indicative value range based on:
1. AVM baseline (from PropertyData or local sales comparables)
2. Feature adjustments (configurable constants)
3. Condition scoring (age + emoji modifier)
4. Situation confidence band

All monetary constants are configurable — stored here as defaults,
intended to be calibrated over time as the platform accumulates data.
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.user_property import UserProperty, PropertyValuation
from backend.models.sales_history import SalesHistory

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURABLE CONSTANTS — all £ amounts are adjustments to the baseline
# ============================================================================

# Section 2: Feature adjustments
FEATURE_ADJUSTMENTS = {
    'parking': {
        'none': 0,
        'on_street_permit': 2000,
        'allocated_on_street': 3000,
        'driveway': 6000,
        'single_garage': 10000,
        'double_garage': 18000,
    },
    'garden': {
        'none': -3000,
        'communal': 0,
        'small_private': 2000,
        'medium_private': 5000,
        'large_private': 8000,
    },
    'garden_aspect': {
        'unknown': 0,
        'north': -1000,
        'east': 0,
        'west': 2000,
        'south': 4000,
        'south_west': 5000,
    },
    'epc_rating': {
        'A': 5000, 'B': 5000, 'C': 2000, 'D': 0,
        'E': -5000, 'F': -12000, 'G': -12000, 'unknown': 0,
    },
    'heating': {
        'gas_central': 0,
        'electric': -3000,
        'heat_pump': 5000,
        'other': -2000,
        'none': -8000,
    },
    'extension': {
        'none': 0,
        'single_storey_rear': 15000,
        'double_storey_rear': 25000,
        'loft_conversion': 20000,
        'side_return': 12000,
        'other': 10000,
    },
    'lease': {
        # Applied as percentage of baseline, not flat £
        'freehold': 0,
        'leasehold_80plus': 0,
        'leasehold_70_80': -0.15,  # -15%
        'leasehold_under_70': -0.25,  # -25%
    },
    'occupancy': {
        'owner_occupied': 0,
        'tenanted_ast': 0,
        'tenanted_sitting': -0.20,  # -20%
        'vacant': 0,
    },
}

# Section 3: Condition scoring — £ per point per attribute
CONDITION_WEIGHTS = {
    'kitchen': 8000,
    'bathrooms': 4000,
    'boiler': 7000,
    'windows': 3000,
    'roof': 9000,
    'decoration': 1500,
    'garden_condition': 2500,
}

# Age-to-score mapping
AGE_SCORE = {
    (0, 3): 2,
    (4, 6): 1,
    (7, 10): 0,
    (11, 15): -1,
    (16, 999): -2,
}

# Emoji modifier (max ±1 shift)
EMOJI_MODIFIER = {
    'poor': -1,
    'below_average': 0,
    'average': 0,
    'good': 0,
    'excellent': 1,
}

# Section 4: Situation band — adjusts confidence range width
SITUATION_ADJUSTMENTS = {
    'motivated': {'band_shift': -0.05, 'label': 'Motivated seller'},    # widen down 5%
    'standard': {'band_shift': 0, 'label': 'Standard'},
    'unmotivated': {'band_shift': 0.02, 'label': 'No urgency'},         # slightly tighter
}

# Standard confidence band: ±5% of midpoint
DEFAULT_BAND_PCT = 0.05


def _age_to_score(year_installed: Optional[int]) -> int:
    """Convert installation year to base condition score."""
    if not year_installed:
        return 0  # unknown = average
    age = datetime.utcnow().year - year_installed
    for (lo, hi), score in AGE_SCORE.items():
        if lo <= age <= hi:
            return score
    return -2  # very old


def _condition_score(attr: str, year_installed: Optional[int], emoji: str) -> int:
    """Calculate combined condition score for one attribute. Returns score × weight in £."""
    base = _age_to_score(year_installed)
    modifier = EMOJI_MODIFIER.get(emoji, 0)

    # Clamp combined score: emoji can't make a 20yr kitchen score above -1
    combined = base + modifier
    combined = max(base - 1, min(base + 1, combined))  # ±1 from base

    weight = CONDITION_WEIGHTS.get(attr, 0)
    return combined * weight


def _get_avm_baseline(db: Session, postcode: str, property_type: str, bedrooms: int) -> Optional[float]:
    """
    Get AVM baseline. Tries PropertyData API first, falls back to local comparables.
    """
    # Try PropertyData API if configured
    pd_api_key = os.environ.get('PROPERTYDATA_API_KEY')
    if pd_api_key:
        try:
            import requests
            resp = requests.get(
                'https://api.propertydata.co.uk/valuation-sale',
                params={
                    'key': pd_api_key,
                    'postcode': postcode,
                    'property_type': property_type,
                    'bedrooms': bedrooms,
                },
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                if data.get('result'):
                    return float(data['result'].get('estimate', 0))
        except Exception as e:
            logger.warning("PropertyData AVM failed for %s: %s", postcode, e)

    # Fallback: local sales comparables (median of same type+beds in same outward code, last 2 years)
    from sqlalchemy import func
    from datetime import timedelta

    outward = postcode.split(' ')[0] if ' ' in postcode else postcode[:4]
    two_years_ago = (datetime.utcnow() - timedelta(days=730)).date()

    type_map = {
        'detached': 'detached', 'semi_detached': 'semi-detached', 'semi-detached': 'semi-detached',
        'terraced': 'terraced', 'end_of_terrace': 'terraced',
        'flat': 'flat', 'maisonette': 'flat', 'bungalow': 'detached',
    }
    mapped_type = type_map.get(property_type, property_type)

    prices = db.query(SalesHistory.sale_price).filter(
        SalesHistory.postcode.like(f'{outward}%'),
        SalesHistory.property_type == mapped_type,
        SalesHistory.sale_date >= two_years_ago,
        SalesHistory.sale_price > 0,
    ).order_by(SalesHistory.sale_price).all()

    if prices:
        values = [p[0] for p in prices]
        median = values[len(values) // 2]
        return float(median)

    # Last resort: any type in the area
    all_prices = db.query(SalesHistory.sale_price).filter(
        SalesHistory.postcode.like(f'{outward}%'),
        SalesHistory.sale_date >= two_years_ago,
        SalesHistory.sale_price > 0,
    ).order_by(SalesHistory.sale_price).all()

    if all_prices:
        values = [p[0] for p in all_prices]
        return float(values[len(values) // 2])

    return None


def calculate_valuation(db: Session, user_property: UserProperty, answers: dict) -> dict:
    """
    Run the full valuation calculation.

    Args:
        db: Database session
        user_property: The property being valued
        answers: Dict with all wizard answers from sections 1-5

    Returns:
        Dict with avm_baseline, feature_adjustment, condition_adjustment,
        situation_band, range_low, range_mid, range_high, breakdown
    """
    postcode = user_property.postcode.upper().strip()
    prop_type = user_property.property_type
    bedrooms = user_property.bedrooms

    # 1. AVM baseline
    avm = _get_avm_baseline(db, postcode, prop_type, bedrooms)
    if not avm:
        return {'error': 'Could not determine baseline value for this postcode and property type'}

    avm_source = 'propertydata' if os.environ.get('PROPERTYDATA_API_KEY') else 'local_comparables'

    # 2. Feature adjustments
    features = answers.get('features', {})
    feature_total = 0
    feature_breakdown = []

    for category, value in features.items():
        if category in FEATURE_ADJUSTMENTS and value in FEATURE_ADJUSTMENTS[category]:
            adj = FEATURE_ADJUSTMENTS[category][value]
            if isinstance(adj, float) and -1 < adj < 1:
                # Percentage adjustment
                adj_amount = avm * adj
                feature_total += adj_amount
                feature_breakdown.append({'item': category, 'value': value, 'adjustment': round(adj_amount)})
            else:
                feature_total += adj
                feature_breakdown.append({'item': category, 'value': value, 'adjustment': adj})

    # Extension
    extension = answers.get('basics', {}).get('extension_type', 'none')
    if extension in FEATURE_ADJUSTMENTS.get('extension', {}):
        adj = FEATURE_ADJUSTMENTS['extension'][extension]
        feature_total += adj
        feature_breakdown.append({'item': 'extension', 'value': extension, 'adjustment': adj})

    # Lease adjustment
    tenure = user_property.tenure
    lease_years = user_property.lease_years_remaining
    if tenure == 'leasehold' and lease_years:
        if lease_years < 70:
            key = 'leasehold_under_70'
        elif lease_years < 80:
            key = 'leasehold_70_80'
        else:
            key = 'leasehold_80plus'
        pct = FEATURE_ADJUSTMENTS['lease'].get(key, 0)
        if pct:
            adj_amount = avm * pct
            feature_total += adj_amount
            feature_breakdown.append({'item': 'lease', 'value': f'{lease_years} years', 'adjustment': round(adj_amount)})

    # Sitting tenant
    occupancy = answers.get('situation', {}).get('occupancy', 'owner_occupied')
    occ_pct = FEATURE_ADJUSTMENTS['occupancy'].get(occupancy, 0)
    if occ_pct:
        adj_amount = avm * occ_pct
        feature_total += adj_amount
        feature_breakdown.append({'item': 'occupancy', 'value': occupancy, 'adjustment': round(adj_amount)})

    # 3. Condition scoring
    conditions = answers.get('condition', {})
    condition_total = 0
    condition_breakdown = []

    for attr in CONDITION_WEIGHTS:
        attr_data = conditions.get(attr, {})
        year = attr_data.get('year_installed')
        emoji = attr_data.get('condition', 'average')
        adj = _condition_score(attr, year, emoji)
        condition_total += adj
        condition_breakdown.append({
            'item': attr,
            'year': year,
            'condition': emoji,
            'score': _age_to_score(year) + EMOJI_MODIFIER.get(emoji, 0),
            'adjustment': adj,
        })

    # 4. Situation band
    situation = answers.get('situation', {})
    motivation = situation.get('motivation', 'standard')
    timeline = situation.get('timeline', 'no_urgency')

    # Classify as motivated/standard/unmotivated
    if motivation in ('financial', 'inherited') or timeline == 'asap':
        sit_key = 'motivated'
    elif motivation == 'curious' or timeline in ('12_months', 'no_urgency'):
        sit_key = 'unmotivated'
    else:
        sit_key = 'standard'

    sit_config = SITUATION_ADJUSTMENTS[sit_key]
    band_shift = sit_config['band_shift']

    # 5. Calculate final range
    midpoint = avm + feature_total + condition_total
    band_pct = DEFAULT_BAND_PCT + abs(band_shift)

    range_low = round(midpoint * (1 - band_pct))
    range_high = round(midpoint * (1 + band_pct))

    # Apply situation shift direction
    if band_shift < 0:
        # Motivated: widen downward
        range_low = round(midpoint * (1 - band_pct - abs(band_shift)))

    range_mid = round(midpoint)

    return {
        'avm_baseline': round(avm),
        'avm_source': avm_source,
        'feature_adjustment': round(feature_total),
        'feature_breakdown': feature_breakdown,
        'condition_adjustment': round(condition_total),
        'condition_breakdown': condition_breakdown,
        'situation_band': sit_config['label'],
        'situation_band_pct': round(band_shift * 100, 1),
        'range_low': range_low,
        'range_mid': range_mid,
        'range_high': range_high,
    }


def save_valuation(db: Session, user_property_id: int, user_id: int,
                   answers: dict, result: dict) -> PropertyValuation:
    """Save a valuation result (versioned — never overwrites)."""
    valuation = PropertyValuation(
        user_property_id=user_property_id,
        user_id=user_id,
        answers_json=json.dumps(answers),
        avm_baseline=result.get('avm_baseline'),
        avm_source=result.get('avm_source'),
        feature_adjustment=result.get('feature_adjustment'),
        condition_adjustment=result.get('condition_adjustment'),
        situation_band=result.get('situation_band'),
        situation_band_pct=result.get('situation_band_pct'),
        range_low=result.get('range_low'),
        range_mid=result.get('range_mid'),
        range_high=result.get('range_high'),
        created_at=datetime.utcnow(),
    )
    db.add(valuation)
    db.commit()
    db.refresh(valuation)
    return valuation
