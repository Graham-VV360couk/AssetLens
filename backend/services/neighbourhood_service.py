"""
Neighbourhood Enrichment Service

Enriches properties with pre-computed neighbourhood data from imported datasets:
- Postcode lookup (LSOA, IMD, coordinates backfill)
- Broadband coverage
- Crime stats and trends
- Nearest schools
- Nearest transport stops
- Planning designations (flood, conservation, Article 4, listed, green belt)

Usage:
    python -m backend.services.neighbourhood_service              # enrich all unenriched
    python -m backend.services.neighbourhood_service --all        # re-enrich everything
    python -m backend.services.neighbourhood_service --id 123     # enrich single property
"""
import argparse
import logging
import math
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import func, text, and_, or_
from sqlalchemy.orm import Session

from backend.models.base import SessionLocal
from backend.models.property import Property
from backend.models.postcode import Postcode
from backend.models.broadband import BroadbandCoverage
from backend.models.crime import Crime
from backend.models.school import School
from backend.models.transport_stop import TransportStop
from backend.models.planning_designation import PlanningDesignation

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Radius for planning designation checks (degrees, ~1 mile ≈ 0.0145 degrees)
PLANNING_RADIUS_DEG = 0.0145
# Radius for school/transport search (degrees, ~3 miles)
SEARCH_RADIUS_DEG = 0.045
# Miles per degree latitude (approximate for UK)
MI_PER_DEG_LAT = 69.0
MI_PER_DEG_LNG_UK = 43.0  # at ~53°N latitude


def _haversine_miles(lat1, lng1, lat2, lng2):
    """Calculate distance in miles between two lat/lng points."""
    R = 3959  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _enrich_postcode(db: Session, prop: Property):
    """Look up postcode → backfill coords, LSOA, IMD, rural/urban."""
    if not prop.postcode:
        return

    pc = db.query(Postcode).filter(Postcode.postcode == prop.postcode).first()
    if not pc:
        # Try without space variations
        normalised = prop.postcode.strip().upper()
        pc = db.query(Postcode).filter(
            func.replace(Postcode.postcode, ' ', '') == normalised.replace(' ', '')
        ).first()

    if not pc:
        return

    prop.lsoa_code = pc.lsoa11_code or pc.lsoa21_code
    prop.msoa_code = pc.msoa11_code or pc.msoa21_code
    prop.lad_code = pc.lad_code
    prop.imd_rank = pc.imd_rank
    prop.rural_urban = pc.rural_urban

    # Backfill coordinates if missing
    if not prop.latitude and pc.latitude:
        prop.latitude = pc.latitude
        prop.longitude = pc.longitude


def _enrich_broadband(db: Session, prop: Property):
    """Look up broadband coverage by postcode."""
    if not prop.postcode:
        return

    bb = db.query(BroadbandCoverage).filter(
        BroadbandCoverage.postcode == prop.postcode
    ).first()
    if not bb:
        # Try without space
        normalised = prop.postcode.strip().upper()
        bb = db.query(BroadbandCoverage).filter(
            func.replace(BroadbandCoverage.postcode, ' ', '') == normalised.replace(' ', '')
        ).first()

    if not bb:
        return

    prop.broadband_gigabit_pct = bb.gigabit_availability
    prop.broadband_sfbb_pct = bb.sfbb_availability
    prop.broadband_below_uso_pct = bb.pct_below_uso


def _enrich_crime(db: Session, prop: Property):
    """Calculate crime stats from LSOA or nearby coordinates."""
    if not prop.lsoa_code:
        return

    # Count crimes in last 12 months
    one_year_ago = (datetime.utcnow() - timedelta(days=365)).date()
    two_years_ago = (datetime.utcnow() - timedelta(days=730)).date()

    recent_count = db.query(func.count(Crime.id)).filter(
        Crime.lsoa_code == prop.lsoa_code,
        Crime.month >= one_year_ago,
    ).scalar() or 0

    prior_count = db.query(func.count(Crime.id)).filter(
        Crime.lsoa_code == prop.lsoa_code,
        Crime.month >= two_years_ago,
        Crime.month < one_year_ago,
    ).scalar() or 0

    prop.crime_count_1yr = recent_count

    # Rate band (based on typical LSOA size of ~1500 residents)
    # National average is ~80 crimes per 1000 people per year
    annual_per_1000 = (recent_count / 1.5) if recent_count else 0
    if annual_per_1000 <= 40:
        prop.crime_rate_band = 'Low'
    elif annual_per_1000 <= 70:
        prop.crime_rate_band = 'Below Average'
    elif annual_per_1000 <= 100:
        prop.crime_rate_band = 'Average'
    elif annual_per_1000 <= 140:
        prop.crime_rate_band = 'Above Average'
    else:
        prop.crime_rate_band = 'High'

    # Trend: compare this year vs last year
    if prior_count > 0:
        change_pct = ((recent_count - prior_count) / prior_count) * 100
        if change_pct <= -10:
            prop.crime_trend = 'Improving'
        elif change_pct <= 5:
            prop.crime_trend = 'Stable'
        elif change_pct <= 20:
            prop.crime_trend = 'Worsening'
        else:
            prop.crime_trend = 'Rising Fast'
    elif recent_count > 0:
        prop.crime_trend = 'No Prior Data'


def _find_nearest_school(db: Session, lat: float, lng: float, phase: str, pc_cache: dict = None):
    """Find nearest school of given phase. Uses raw SQL for speed. Returns (name, distance_mi) or (None, None)."""
    # Use a subquery: join schools to postcodes by postcode, filter by bounding box on postcodes
    result = db.execute(text("""
        SELECT s.establishment_name, p.latitude, p.longitude
        FROM schools s
        JOIN postcodes p ON p.postcode = s.postcode
        WHERE s.phase_of_education ILIKE :phase
          AND p.latitude BETWEEN :lat_min AND :lat_max
          AND p.longitude BETWEEN :lng_min AND :lng_max
          AND p.latitude IS NOT NULL
        LIMIT 50
    """), {
        'phase': f'%{phase}%',
        'lat_min': lat - SEARCH_RADIUS_DEG,
        'lat_max': lat + SEARCH_RADIUS_DEG,
        'lng_min': lng - SEARCH_RADIUS_DEG,
        'lng_max': lng + SEARCH_RADIUS_DEG,
    }).fetchall()

    if not result:
        return None, None

    best_name = None
    best_dist = float('inf')

    for row in result:
        dist = _haversine_miles(lat, lng, row[1], row[2])
        if dist < best_dist:
            best_dist = dist
            best_name = row[0]

    if best_name and best_dist < 5.0:
        return best_name, round(best_dist, 2)
    return None, None


def _find_nearby_schools(db: Session, lat: float, lng: float, per_phase: int = 3) -> list:
    """Find closest N schools per phase. Returns list of dicts."""
    result = db.execute(text("""
        SELECT s.establishment_name, s.phase_of_education, s.postcode,
               s.is_boarding, s.is_selective, s.gender, s.religious_character,
               s.number_of_pupils, p.latitude, p.longitude
        FROM schools s
        JOIN postcodes p ON p.postcode = s.postcode
        WHERE p.latitude BETWEEN :lat_min AND :lat_max
          AND p.longitude BETWEEN :lng_min AND :lng_max
          AND p.latitude IS NOT NULL
          AND s.phase_of_education IS NOT NULL
    """), {
        'lat_min': lat - SEARCH_RADIUS_DEG, 'lat_max': lat + SEARCH_RADIUS_DEG,
        'lng_min': lng - SEARCH_RADIUS_DEG, 'lng_max': lng + SEARCH_RADIUS_DEG,
    }).fetchall()

    schools = []
    for r in result:
        dist = _haversine_miles(lat, lng, r[8], r[9])
        schools.append({
            'name': r[0], 'phase': r[1], 'postcode': r[2],
            'is_boarding': r[3], 'is_selective': r[4], 'gender': r[5],
            'religious_character': r[6], 'number_of_pupils': r[7],
            'distance_mi': round(dist, 2),
        })

    schools.sort(key=lambda s: s['distance_mi'])

    # Take closest N per phase
    output = []
    phase_counts = {}
    for s in schools:
        phase = s['phase']
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        if phase_counts[phase] <= per_phase:
            output.append(s)

    return output


def _enrich_schools(db: Session, prop: Property):
    """Find nearest 3 primary and 3 secondary schools."""
    if not prop.latitude or not prop.longitude:
        return

    import json
    schools = _find_nearby_schools(db, prop.latitude, prop.longitude, per_phase=3)
    prop.nearby_schools = json.dumps(schools) if schools else None

    # Also populate the single-nearest fields for backwards compat
    for s in schools:
        if 'Primary' in (s.get('phase') or ''):
            if not prop.nearest_primary_name:
                prop.nearest_primary_name = s['name']
                prop.nearest_primary_distance_mi = s['distance_mi']
        elif 'Secondary' in (s.get('phase') or '') or 'Not applicable' in (s.get('phase') or ''):
            if not prop.nearest_secondary_name:
                prop.nearest_secondary_name = s['name']
                prop.nearest_secondary_distance_mi = s['distance_mi']


def _enrich_transport(db: Session, prop: Property):
    """Find nearest rail stations and bus stops."""
    if not prop.latitude or not prop.longitude:
        return

    import json
    lat, lng = prop.latitude, prop.longitude
    transport = []

    # Rail stations (RLY = rail, MET = metro/tram)
    rail_types = ('RLY', 'MET', 'PLT')
    stations = db.query(TransportStop).filter(
        TransportStop.stop_type.in_(rail_types),
        TransportStop.status == 'active',
        TransportStop.latitude.between(lat - SEARCH_RADIUS_DEG, lat + SEARCH_RADIUS_DEG),
        TransportStop.longitude.between(lng - SEARCH_RADIUS_DEG, lng + SEARCH_RADIUS_DEG),
    ).all()

    for s in stations:
        dist = _haversine_miles(lat, lng, s.latitude, s.longitude)
        transport.append({
            'name': s.name, 'stop_type': s.stop_type,
            'distance_mi': round(dist, 2),
        })

    # Bus stops — tighter radius, top 5
    bus = db.query(TransportStop).filter(
        TransportStop.stop_type == 'BCT',
        TransportStop.status == 'active',
        TransportStop.latitude.between(lat - PLANNING_RADIUS_DEG, lat + PLANNING_RADIUS_DEG),
        TransportStop.longitude.between(lng - PLANNING_RADIUS_DEG, lng + PLANNING_RADIUS_DEG),
    ).all()

    bus_list = []
    for s in bus:
        dist = _haversine_miles(lat, lng, s.latitude, s.longitude)
        bus_list.append({'name': s.name, 'stop_type': 'BCT', 'distance_mi': round(dist, 2)})
    bus_list.sort(key=lambda x: x['distance_mi'])
    transport.extend(bus_list[:5])

    transport.sort(key=lambda x: x['distance_mi'])
    prop.nearby_transport = json.dumps(transport) if transport else None

    # Populate single-nearest fields for backwards compat
    rail_sorted = [t for t in transport if t['stop_type'] != 'BCT']
    if rail_sorted:
        prop.nearest_station_name = rail_sorted[0]['name']
        prop.nearest_station_distance_mi = rail_sorted[0]['distance_mi']
        prop.nearest_station_type = rail_sorted[0]['stop_type']
    bus_sorted = [t for t in transport if t['stop_type'] == 'BCT']
    if bus_sorted:
        prop.nearest_bus_name = bus_sorted[0]['name']
        prop.nearest_bus_distance_mi = bus_sorted[0]['distance_mi']


def _enrich_planning(db: Session, prop: Property):
    """Check planning designations within radius of property."""
    if not prop.latitude or not prop.longitude:
        return

    import json
    lat, lng = prop.latitude, prop.longitude

    nearby = db.query(
        PlanningDesignation.dataset,
        PlanningDesignation.name,
        PlanningDesignation.flood_risk_level,
        PlanningDesignation.listed_building_grade,
        PlanningDesignation.latitude,
        PlanningDesignation.longitude,
    ).filter(
        PlanningDesignation.latitude.between(lat - PLANNING_RADIUS_DEG, lat + PLANNING_RADIUS_DEG),
        PlanningDesignation.longitude.between(lng - PLANNING_RADIUS_DEG, lng + PLANNING_RADIUS_DEG),
    ).all()

    datasets_found = set()
    flood_level = None
    listed_grade = None
    flags = []
    seen_datasets = {}
    seen_flood_levels = {}   # flood_risk_level -> best distance
    listed_entries = []      # collect then trim

    for row in nearby:
        datasets_found.add(row.dataset)
        dist = _haversine_miles(lat, lng, row.latitude, row.longitude) if row.latitude else None

        if row.dataset == 'flood-risk-zone' and row.flood_risk_level:
            if not flood_level or str(row.flood_risk_level) > str(flood_level):
                flood_level = row.flood_risk_level
        if row.dataset == 'listed-building' and row.listed_building_grade:
            listed_grade = row.listed_building_grade

        entry = {
            'dataset': row.dataset, 'name': row.name,
            'distance_mi': round(dist, 2) if dist else None,
            'flood_risk_level': row.flood_risk_level,
            'listed_building_grade': row.listed_building_grade,
        }

        if row.dataset == 'flood-risk-zone':
            lvl = row.flood_risk_level or 'unknown'
            prev = seen_flood_levels.get(lvl)
            if prev is None or (dist is not None and dist < prev):
                seen_flood_levels[lvl] = dist
                flags = [f for f in flags
                         if not (f['dataset'] == 'flood-risk-zone'
                                 and (f['flood_risk_level'] or 'unknown') == lvl)]
                flags.append(entry)
        elif row.dataset == 'listed-building':
            listed_entries.append((dist if dist is not None else 999, entry))
        else:
            if row.dataset not in seen_datasets or (dist and dist < seen_datasets[row.dataset]):
                seen_datasets[row.dataset] = dist
                flags = [f for f in flags if f['dataset'] != row.dataset]
                flags.append(entry)

    # Keep only the 5 closest listed buildings
    listed_entries.sort(key=lambda x: x[0])
    flags.extend(e for _, e in listed_entries[:5])

    flags.sort(key=lambda f: f.get('distance_mi') or 999)
    prop.planning_flags = json.dumps(flags) if flags else None

    # Boolean/simple fields for quick access
    prop.in_conservation_area = 'conservation-area' in datasets_found
    prop.in_flood_zone = flood_level
    prop.in_green_belt = 'green-belt' in datasets_found
    prop.has_article4 = 'article-4-direction-area' in datasets_found
    prop.is_listed_building = listed_grade


def enrich_property(db: Session, prop: Property):
    """Run all enrichment steps on a single property."""
    _enrich_postcode(db, prop)
    _enrich_broadband(db, prop)
    _enrich_crime(db, prop)
    _enrich_schools(db, prop)
    _enrich_transport(db, prop)
    _enrich_planning(db, prop)
    prop.neighbourhood_enriched_at = datetime.utcnow()


def enrich_all(only_unenriched: bool = True, property_id: int = None):
    """Enrich all properties (or just unenriched ones)."""
    db = SessionLocal()
    try:
        query = db.query(Property)

        if property_id:
            query = query.filter(Property.id == property_id)
        elif only_unenriched:
            query = query.filter(Property.neighbourhood_enriched_at.is_(None))

        properties = query.all()
        total = len(properties)
        logger.info("Enriching %d properties", total)

        success = 0
        errors = 0

        for idx, prop in enumerate(properties, 1):
            try:
                enrich_property(db, prop)
                success += 1

                if idx % 50 == 0 or idx == total:
                    db.commit()
                    logger.info("[%d/%d] %d enriched, %d errors", idx, total, success, errors)

            except Exception as e:
                logger.warning("Error enriching property %d (%s): %s", prop.id, prop.postcode, e)
                errors += 1
                db.rollback()

        db.commit()
        logger.info("Enrichment complete: %d success, %d errors out of %d", success, errors, total)
        return {'total': total, 'success': success, 'errors': errors}

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Enrich properties with neighbourhood data')
    parser.add_argument('--all', action='store_true', help='Re-enrich all properties')
    parser.add_argument('--id', type=int, help='Enrich single property by ID')
    args = parser.parse_args()

    if args.id:
        enrich_all(property_id=args.id)
    else:
        enrich_all(only_unenriched=not args.all)


if __name__ == '__main__':
    main()
