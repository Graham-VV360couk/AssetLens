"""
Neighbourhood Report Service

Generates a comprehensive neighbourhood intelligence report for any UK postcode.
Works for ANY address — not just properties in our database.

Returns: schools, crime, broadband, transport, planning constraints,
         sales history, nearby for-sale properties.
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.models.postcode import Postcode
from backend.models.broadband import BroadbandCoverage
from backend.models.crime import Crime
from backend.models.school import School
from backend.models.transport_stop import TransportStop
from backend.models.planning_designation import PlanningDesignation
from backend.models.sales_history import SalesHistory
from backend.models.property import Property

logger = logging.getLogger(__name__)

# ~1 mile in degrees latitude
MI_1 = 0.0145
# ~3 miles
MI_3 = 0.045

R_EARTH_MI = 3959


def _haversine(lat1, lng1, lat2, lng2):
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R_EARTH_MI * 2 * math.asin(math.sqrt(a))


def _imd_band(rank: int) -> str:
    """Convert IMD rank to human-readable band. England has 32,844 LSOAs."""
    if not rank:
        return 'Unknown'
    if rank <= 3284:
        return 'Most Deprived 10%'
    if rank <= 6569:
        return 'Most Deprived 20%'
    if rank <= 16422:
        return 'Below Average'
    if rank <= 26275:
        return 'Above Average'
    return 'Least Deprived 20%'


def _lookup_postcode(db: Session, postcode: str) -> Optional[Postcode]:
    """Find postcode record, trying exact then normalised match."""
    pc = db.query(Postcode).filter(Postcode.postcode == postcode).first()
    if pc:
        return pc
    normalised = postcode.strip().upper().replace(' ', '')
    return db.query(Postcode).filter(
        func.replace(Postcode.postcode, ' ', '') == normalised
    ).first()


def _get_broadband(db: Session, postcode: str) -> dict:
    bb = db.query(BroadbandCoverage).filter(BroadbandCoverage.postcode == postcode).first()
    if not bb:
        normalised = postcode.strip().upper().replace(' ', '')
        bb = db.query(BroadbandCoverage).filter(
            func.replace(BroadbandCoverage.postcode, ' ', '') == normalised
        ).first()
    if not bb:
        return {}
    return {
        'broadband_gigabit_pct': bb.gigabit_availability,
        'broadband_sfbb_pct': bb.sfbb_availability,
        'broadband_below_uso_pct': bb.pct_below_uso,
    }


def _get_crime(db: Session, lsoa_code: str) -> dict:
    if not lsoa_code:
        return {}

    one_yr = (datetime.utcnow() - timedelta(days=365)).date()
    two_yr = (datetime.utcnow() - timedelta(days=730)).date()

    recent = db.query(func.count(Crime.id)).filter(
        Crime.lsoa_code == lsoa_code, Crime.month >= one_yr
    ).scalar() or 0

    prior = db.query(func.count(Crime.id)).filter(
        Crime.lsoa_code == lsoa_code, Crime.month >= two_yr, Crime.month < one_yr
    ).scalar() or 0

    # Rate band
    per_1000 = (recent / 1.5) if recent else 0
    if per_1000 <= 40:
        band = 'Low'
    elif per_1000 <= 70:
        band = 'Below Average'
    elif per_1000 <= 100:
        band = 'Average'
    elif per_1000 <= 140:
        band = 'Above Average'
    else:
        band = 'High'

    # Trend
    trend = 'No Prior Data'
    if prior > 0:
        change = ((recent - prior) / prior) * 100
        if change <= -10:
            trend = 'Improving'
        elif change <= 5:
            trend = 'Stable'
        elif change <= 20:
            trend = 'Worsening'
        else:
            trend = 'Rising Fast'

    # Breakdown by type (last 12 months)
    by_type = db.query(Crime.crime_type, func.count(Crime.id)).filter(
        Crime.lsoa_code == lsoa_code, Crime.month >= one_yr
    ).group_by(Crime.crime_type).order_by(func.count(Crime.id).desc()).all()

    # Monthly trend (last 24 months)
    monthly = db.query(Crime.month, func.count(Crime.id)).filter(
        Crime.lsoa_code == lsoa_code, Crime.month >= two_yr
    ).group_by(Crime.month).order_by(Crime.month).all()

    return {
        'total_1yr': recent,
        'rate_band': band,
        'trend': trend,
        'by_type': [{'type': t, 'count': c} for t, c in by_type],
        'monthly_trend': [{'month': str(m), 'count': c} for m, c in monthly],
    }


def _get_schools(db: Session, lat: float, lng: float, radius_deg: float = MI_3) -> list:
    """Get closest 3 schools per phase."""
    results = db.execute(text("""
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
        'lat_min': lat - radius_deg, 'lat_max': lat + radius_deg,
        'lng_min': lng - radius_deg, 'lng_max': lng + radius_deg,
    }).fetchall()

    schools_with_dist = []
    for r in results:
        dist = _haversine(lat, lng, r[8], r[9])
        schools_with_dist.append({
            'name': r[0],
            'phase': r[1],
            'postcode': r[2],
            'is_boarding': r[3],
            'is_selective': r[4],
            'gender': r[5],
            'religious_character': r[6],
            'number_of_pupils': r[7],
            'latitude': r[8],
            'longitude': r[9],
            'distance_mi': round(dist, 2),
        })

    # Sort by distance, take closest 3 per phase
    schools_with_dist.sort(key=lambda s: s['distance_mi'])
    output = []
    phase_counts = {}
    for s in schools_with_dist:
        phase = s['phase']
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        if phase_counts[phase] <= 3:
            output.append(s)

    return output


def _get_transport(db: Session, lat: float, lng: float) -> list:
    """Get nearest rail stations and bus stops."""
    stops = []

    # Rail/metro — wider search
    rail = db.query(TransportStop).filter(
        TransportStop.stop_type.in_(('RLY', 'MET', 'PLT')),
        TransportStop.status == 'active',
        TransportStop.latitude.between(lat - MI_3, lat + MI_3),
        TransportStop.longitude.between(lng - MI_3, lng + MI_3),
    ).all()

    for s in rail:
        dist = _haversine(lat, lng, s.latitude, s.longitude)
        stops.append({
            'name': s.name, 'stop_type': s.stop_type,
            'distance_mi': round(dist, 2),
            'latitude': s.latitude, 'longitude': s.longitude,
        })

    # Bus — tighter search, limit to nearest 5
    bus = db.query(TransportStop).filter(
        TransportStop.stop_type == 'BCT',
        TransportStop.status == 'active',
        TransportStop.latitude.between(lat - MI_1, lat + MI_1),
        TransportStop.longitude.between(lng - MI_1, lng + MI_1),
    ).all()

    bus_with_dist = []
    for s in bus:
        dist = _haversine(lat, lng, s.latitude, s.longitude)
        bus_with_dist.append({
            'name': s.name, 'stop_type': 'BCT',
            'distance_mi': round(dist, 2),
            'latitude': s.latitude, 'longitude': s.longitude,
        })
    bus_with_dist.sort(key=lambda x: x['distance_mi'])
    stops.extend(bus_with_dist[:5])

    stops.sort(key=lambda x: x['distance_mi'])
    return stops


def _get_planning(db: Session, lat: float, lng: float) -> list:
    """Get planning designations within ~1 mile."""
    rows = db.query(
        PlanningDesignation.dataset,
        PlanningDesignation.name,
        PlanningDesignation.flood_risk_level,
        PlanningDesignation.listed_building_grade,
        PlanningDesignation.latitude,
        PlanningDesignation.longitude,
    ).filter(
        PlanningDesignation.latitude.between(lat - MI_1, lat + MI_1),
        PlanningDesignation.longitude.between(lng - MI_1, lng + MI_1),
    ).all()

    # Deduplicate by dataset (show closest per type, except flood/listed which show all)
    flags = []
    seen_datasets = {}
    for r in rows:
        dist = _haversine(lat, lng, r.latitude, r.longitude) if r.latitude else None
        entry = {
            'dataset': r.dataset,
            'name': r.name,
            'distance_mi': round(dist, 2) if dist else None,
            'flood_risk_level': r.flood_risk_level,
            'listed_building_grade': r.listed_building_grade,
        }

        # For flood/listed, keep all. For others, keep closest.
        if r.dataset in ('flood-risk-zone', 'listed-building'):
            flags.append(entry)
        else:
            if r.dataset not in seen_datasets or (dist and dist < seen_datasets[r.dataset]):
                seen_datasets[r.dataset] = dist
                # Replace previous entry for this dataset
                flags = [f for f in flags if f['dataset'] != r.dataset]
                flags.append(entry)

    flags.sort(key=lambda f: f.get('distance_mi') or 999)
    return flags


def _get_sales_history(db: Session, postcode: str) -> tuple:
    """Get sales history for the postcode + area averages."""
    # Exact postcode matches
    history = db.query(SalesHistory).filter(
        SalesHistory.postcode == postcode,
        SalesHistory.sale_price > 0,
    ).order_by(SalesHistory.sale_date.desc()).limit(30).all()

    # Area averages (same outward code)
    outward = postcode.split(' ')[0] if ' ' in postcode else postcode[:4]
    one_yr = (datetime.utcnow() - timedelta(days=365)).date()
    five_yr = (datetime.utcnow() - timedelta(days=1825)).date()

    avg_1yr = db.query(func.avg(SalesHistory.sale_price)).filter(
        SalesHistory.postcode.like(f'{outward}%'),
        SalesHistory.sale_date >= one_yr,
        SalesHistory.sale_price > 0,
    ).scalar()

    avg_5yr = db.query(func.avg(SalesHistory.sale_price)).filter(
        SalesHistory.postcode.like(f'{outward}%'),
        SalesHistory.sale_date >= five_yr,
        SalesHistory.sale_price > 0,
    ).scalar()

    return history, avg_1yr, avg_5yr


def _get_nearby_properties(db: Session, lat: float, lng: float, radius_mi: float = 1.0) -> list:
    """Find properties for sale within radius."""
    radius_deg = radius_mi * MI_1
    props = db.query(Property).filter(
        Property.status == 'active',
        Property.latitude.between(lat - radius_deg, lat + radius_deg),
        Property.longitude.between(lng - radius_deg, lng + radius_deg),
    ).limit(20).all()

    results = []
    for p in props:
        dist = _haversine(lat, lng, p.latitude, p.longitude)
        results.append({
            'id': p.id,
            'address': p.address,
            'postcode': p.postcode,
            'asking_price': p.asking_price,
            'property_type': p.property_type,
            'bedrooms': p.bedrooms,
            'image_url': p.image_url,
            'distance_mi': round(dist, 2),
            'status': p.status,
        })

    results.sort(key=lambda x: x['distance_mi'])
    return results


def generate_report(db: Session, postcode: str) -> dict:
    """Generate a full neighbourhood report for a postcode."""
    pc = _lookup_postcode(db, postcode)
    if not pc:
        return {'postcode': postcode, 'error': 'Postcode not found'}

    lat, lng = pc.latitude, pc.longitude
    lsoa = pc.lsoa11_code or pc.lsoa21_code

    report = {
        'postcode': pc.postcode,
        'latitude': lat,
        'longitude': lng,
        'lsoa_code': lsoa,
        'msoa_code': pc.msoa11_code or pc.msoa21_code,
        'lad_code': pc.lad_code,
        'imd_rank': pc.imd_rank,
        'imd_band': _imd_band(pc.imd_rank) if pc.imd_rank else None,
        'rural_urban': pc.rural_urban,
    }

    # Broadband
    report.update(_get_broadband(db, pc.postcode))

    # Crime
    if lsoa:
        report['crime'] = _get_crime(db, lsoa)

    # Crime heat map points (lat/lng of all crimes in the area for past 12 months)
    if lat and lng:
        one_yr = (datetime.utcnow() - timedelta(days=365)).date()
        crime_points = db.query(Crime.latitude, Crime.longitude).filter(
            Crime.latitude.between(lat - MI_1, lat + MI_1),
            Crime.longitude.between(lng - MI_1, lng + MI_1),
            Crime.latitude.isnot(None),
            Crime.month >= one_yr,
        ).limit(500).all()
        report['crime_heatmap'] = [[c.latitude, c.longitude, 0.5] for c in crime_points]

    # Schools (closest 3 per phase)
    if lat and lng:
        report['schools'] = _get_schools(db, lat, lng)
        report['transport'] = _get_transport(db, lat, lng)
        report['planning'] = _get_planning(db, lat, lng)
        report['nearby_for_sale'] = _get_nearby_properties(db, lat, lng)

    # Sales history
    history, avg_1yr, avg_5yr = _get_sales_history(db, pc.postcode)
    report['sales_history'] = [
        {
            'id': h.id, 'sale_date': str(h.sale_date), 'sale_price': int(h.sale_price),
            'property_type': h.property_type, 'address': h.address, 'postcode': h.postcode,
        }
        for h in history
    ]
    report['avg_price_1yr'] = round(avg_1yr) if avg_1yr else None
    report['avg_price_5yr'] = round(avg_5yr) if avg_5yr else None

    return report
