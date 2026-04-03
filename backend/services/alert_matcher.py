"""
Alert Matching Engine

Scores properties against user preferences and returns matches.
Used by:
1. GET /api/alerts/matches — on-demand matching for a single user
2. Daily alert job — batch matching for all users with active alerts
3. On-ingest hook — immediate matching when new properties arrive

The scoring uses the same computeWeightedScore logic as the frontend sliders,
implemented server-side in Python.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.property import Property, PropertyScore
from backend.models.user import User
from backend.models.alert_preference import UserAlertPreference

logger = logging.getLogger(__name__)

# Same scoring logic as frontend ScoringSliders.jsx computeWeightedScore
CRIME_BAND_SCORES = {'Low': 100, 'Below Average': 75, 'Average': 50, 'Above Average': 25, 'High': 0}
EPC_SCORES = {'A': 100, 'B': 85, 'C': 70, 'D': 55, 'E': 40, 'F': 20, 'G': 0}


def compute_weighted_score(prop: Property, weights: dict) -> Optional[int]:
    """
    Server-side equivalent of the frontend computeWeightedScore.
    Returns 0-100 match percentage, or None if insufficient data.
    """
    scores = {}

    # Price vs valuation
    score_obj = prop.score if hasattr(prop, 'score') and prop.score else None
    if score_obj and score_obj.price_deviation_pct is not None:
        scores['price'] = max(0, min(100, 50 + score_obj.price_deviation_pct))

    # Yield
    if score_obj and score_obj.gross_yield_pct is not None:
        scores['yield'] = min(100, (score_obj.gross_yield_pct / 12) * 100)

    # Crime
    if prop.crime_rate_band:
        scores['crime'] = CRIME_BAND_SCORES.get(prop.crime_rate_band, 50)

    # Broadband
    if prop.broadband_gigabit_pct is not None:
        scores['broadband'] = prop.broadband_gigabit_pct

    # Schools
    if prop.nearest_primary_distance_mi is not None:
        scores['schools'] = max(0, 100 - (prop.nearest_primary_distance_mi / 5) * 100)

    # Transport
    if prop.nearest_station_distance_mi is not None:
        scores['transport'] = max(0, 100 - (prop.nearest_station_distance_mi / 5) * 100)

    # Flood
    scores['flood'] = 0 if prop.in_flood_zone else 100

    # EPC
    if prop.epc_energy_rating:
        scores['epc'] = EPC_SCORES.get(prop.epc_energy_rating, 50)

    # Planning restrictions
    penalties = sum(1 for x in [
        prop.in_conservation_area, prop.has_article4,
        prop.in_green_belt, prop.is_listed_building,
    ] if x)
    scores['planning'] = max(0, 100 - penalties * 25)

    # Deprivation
    if prop.imd_rank:
        scores['deprivation'] = (prop.imd_rank / 32844) * 100

    # Weighted average
    total_weighted = 0
    total_weight = 0
    for key, weight in weights.items():
        if weight > 0 and key in scores:
            total_weighted += scores[key] * weight
            total_weight += weight

    if total_weight == 0:
        return None

    return round(total_weighted / total_weight)


def _get_match_reasons(prop: Property, scores_detail: dict) -> list:
    """Generate human-readable reasons why this property matched."""
    reasons = []
    if prop.crime_rate_band in ('Low', 'Below Average'):
        reasons.append(f'Low crime ({prop.crime_rate_band})')
    if prop.broadband_gigabit_pct and prop.broadband_gigabit_pct >= 80:
        reasons.append(f'Gigabit broadband ({prop.broadband_gigabit_pct}%)')
    if prop.nearest_station_distance_mi and prop.nearest_station_distance_mi < 1:
        reasons.append(f'Station {prop.nearest_station_distance_mi}mi')
    if prop.nearest_primary_distance_mi and prop.nearest_primary_distance_mi < 0.5:
        reasons.append(f'School {prop.nearest_primary_distance_mi}mi')
    if not prop.in_flood_zone:
        reasons.append('No flood risk')
    if prop.epc_energy_rating in ('A', 'B', 'C'):
        reasons.append(f'EPC {prop.epc_energy_rating}')
    return reasons[:4]  # max 4 reasons


def get_matches_for_user(db: Session, user: User, limit: int = 30) -> list:
    """Get properties matching a user's preferences, ranked by match %."""
    # Get user's scoring weights
    profile = user.profile if hasattr(user, 'profile') else None
    if not profile or not profile.scoring_preferences:
        return []

    try:
        weights = json.loads(profile.scoring_preferences)
    except (json.JSONDecodeError, TypeError):
        return []

    # Get alert preferences
    alert_pref = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user.id
    ).first()
    min_match = alert_pref.min_match_pct if alert_pref else 60

    # Build property query with filters
    query = db.query(Property).filter(Property.status == 'active')

    if alert_pref:
        if alert_pref.max_price:
            query = query.filter(Property.asking_price <= alert_pref.max_price)
        if alert_pref.min_beds:
            query = query.filter(Property.bedrooms >= alert_pref.min_beds)
        if alert_pref.location_filter:
            districts = [d.strip().upper() for d in alert_pref.location_filter.split(',') if d.strip()]
            if districts:
                from sqlalchemy import or_
                query = query.filter(or_(*[Property.postcode.ilike(f'{d}%') for d in districts]))
        if alert_pref.property_types:
            types = [t.strip().lower() for t in alert_pref.property_types.split(',') if t.strip()]
            if types:
                query = query.filter(Property.property_type.in_(types))

    properties = query.limit(500).all()

    # Score each property
    matches = []
    for prop in properties:
        score = compute_weighted_score(prop, weights)
        if score is not None and score >= min_match:
            matches.append({
                'id': prop.id,
                'address': prop.address,
                'postcode': prop.postcode,
                'asking_price': prop.asking_price,
                'property_type': prop.property_type,
                'bedrooms': prop.bedrooms,
                'image_url': prop.image_url,
                'match_pct': score,
                'match_reasons': _get_match_reasons(prop, {}),
            })

    # Sort by match percentage descending
    matches.sort(key=lambda m: m['match_pct'], reverse=True)
    return matches[:limit]


def get_new_matches_since(db: Session, user: User, since: datetime) -> list:
    """Get properties added since a given date that match the user's preferences."""
    profile = user.profile if hasattr(user, 'profile') else None
    if not profile or not profile.scoring_preferences:
        return []

    try:
        weights = json.loads(profile.scoring_preferences)
    except (json.JSONDecodeError, TypeError):
        return []

    alert_pref = db.query(UserAlertPreference).filter(
        UserAlertPreference.user_id == user.id
    ).first()
    min_match = alert_pref.min_match_pct if alert_pref else 60

    # Only new properties since last alert
    new_props = db.query(Property).filter(
        Property.status == 'active',
        Property.date_found >= since.date(),
    ).all()

    matches = []
    for prop in new_props:
        score = compute_weighted_score(prop, weights)
        if score is not None and score >= min_match:
            matches.append({
                'id': prop.id,
                'address': prop.address,
                'postcode': prop.postcode,
                'asking_price': prop.asking_price,
                'property_type': prop.property_type,
                'bedrooms': prop.bedrooms,
                'image_url': prop.image_url,
                'match_pct': score,
                'match_reasons': _get_match_reasons(prop, {}),
            })

    matches.sort(key=lambda m: m['match_pct'], reverse=True)
    return matches


def run_daily_alerts(db: Session):
    """
    Batch job: for each user with active alerts, find new matches
    since their last alert and send email.
    """
    from backend.models.user import User as UserModel

    active_alerts = db.query(UserAlertPreference).filter(
        UserAlertPreference.is_active == True,
        UserAlertPreference.alert_frequency.in_(['daily', 'immediate']),
    ).all()

    logger.info('Processing alerts for %d users', len(active_alerts))

    for alert_pref in active_alerts:
        user = db.query(UserModel).get(alert_pref.user_id)
        if not user or not user.is_active:
            continue

        since = alert_pref.last_alerted_at or (datetime.utcnow() - timedelta(days=1))
        matches = get_new_matches_since(db, user, since)

        if not matches:
            continue

        logger.info('User %s: %d new matches (>=%d%%)',
                    user.email, len(matches), alert_pref.min_match_pct)

        # Send email
        try:
            from backend.services.email_service import send_personalised_alert
            send_personalised_alert(user, matches)
            alert_pref.last_alerted_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.warning('Failed to send alert to %s: %s', user.email, e)
