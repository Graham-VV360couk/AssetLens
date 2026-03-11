"""
Property Attribute Estimation Engine

Estimates and resolves property characteristics from available facts, with
explicit status (known/inferred/estimated/unknown), confidence scores, source
traceability, and explanation text for every field.

Architecture:
    PropertyAttributeEstimator      — orchestrator
    _collect_facts()                — gathers all input data
    _resolve_*()                    — per-attribute estimators
    _detect_contradictions()        — cross-field sanity checks
    AttributeField                  — per-attribute data container
"""
import json
import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.models.property import Property

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Confidence scoring helpers
# ---------------------------------------------------------------------------

def confidence_label(score: float) -> str:
    """Return a display-friendly band label for a 0–1 confidence score."""
    if score >= 0.90:
        return 'very_high'
    elif score >= 0.75:
        return 'high'
    elif score >= 0.55:
        return 'moderate'
    elif score >= 0.35:
        return 'low'
    return 'very_low'


# ---------------------------------------------------------------------------
# Attribute field model
# ---------------------------------------------------------------------------

@dataclass
class AttributeField:
    """
    A single estimated property attribute with full provenance metadata.

    value:      scalar (int/float/str) or dict {'min': N, 'max': N} for ranges,
                or dict {'sqm': N, 'sqft': N} for areas.
    status:     'known' | 'inferred' | 'estimated' | 'unknown'
    confidence: 0.0 – 1.0
    """
    status: str
    value: Any = None
    confidence: float = 0.0
    confidence_label: str = 'very_low'
    source: str = 'none'
    explanation: str = ''
    last_updated: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def unknown(cls, explanation: str = 'No data available.') -> 'AttributeField':
        return cls(
            status='unknown',
            value=None,
            confidence=0.0,
            confidence_label='very_low',
            source='none',
            explanation=explanation,
        )


# ---------------------------------------------------------------------------
# Heuristic rule tables (configurable)
# ---------------------------------------------------------------------------

# (min_sqm_inclusive, max_sqm_exclusive, estimated_beds, confidence)
BEDROOM_RULES: dict[str, list] = {
    'terraced':        [(0, 60, 2, 0.60), (60, 80, 2, 0.70), (80, 110, 3, 0.72),
                        (110, 150, 4, 0.60), (150, 9999, 5, 0.50)],
    'end terrace':     [(0, 65, 2, 0.65), (65, 90, 3, 0.70), (90, 120, 3, 0.68),
                        (120, 160, 4, 0.60), (160, 9999, 5, 0.52)],
    'mid terrace':     [(0, 65, 2, 0.65), (65, 90, 3, 0.70), (90, 110, 3, 0.68),
                        (110, 9999, 4, 0.55)],
    'semi-detached':   [(0, 70, 2, 0.65), (70, 100, 3, 0.75), (100, 130, 3, 0.70),
                        (130, 180, 4, 0.65), (180, 9999, 5, 0.55)],
    'detached':        [(0, 80, 2, 0.60), (80, 120, 3, 0.68), (120, 180, 4, 0.72),
                        (180, 250, 5, 0.65), (250, 9999, 6, 0.55)],
    'flat':            [(0, 45, 1, 0.75), (45, 70, 1, 0.72), (70, 90, 2, 0.68),
                        (90, 120, 2, 0.65), (120, 9999, 3, 0.55)],
    'bungalow':        [(0, 55, 1, 0.65), (55, 80, 2, 0.72), (80, 110, 3, 0.65),
                        (110, 9999, 4, 0.55)],
    'chalet bungalow': [(0, 65, 2, 0.60), (65, 90, 2, 0.65), (90, 130, 3, 0.62),
                        (130, 9999, 4, 0.52)],
    'maisonette':      [(0, 65, 2, 0.60), (65, 90, 2, 0.65), (90, 120, 3, 0.60),
                        (120, 9999, 4, 0.50)],
}

# (min_beds, max_beds, min_bathrooms, max_bathrooms, confidence)
BATHROOM_RULES = [
    (1, 1, 1, 1, 0.78),
    (2, 2, 1, 1, 0.72),
    (3, 3, 1, 2, 0.62),
    (4, 4, 2, 2, 0.58),
    (5, 5, 2, 3, 0.52),
    (6, 99, 2, 3, 0.45),
]

# (type_group, min_beds, max_beds, reception_count, confidence)
RECEPTION_RULES = [
    ('flat',    1, 1, 1, 0.78),
    ('flat',    2, 3, 1, 0.72),
    ('flat',    4, 9, 2, 0.52),
    ('terrace', 1, 2, 1, 0.70),
    ('terrace', 2, 3, 2, 0.70),
    ('terrace', 4, 9, 2, 0.60),
    ('house',   1, 2, 1, 0.68),
    ('house',   2, 3, 2, 0.72),
    ('house',   3, 4, 2, 0.70),
    ('house',   4, 5, 3, 0.62),
    ('house',   5, 9, 3, 0.55),
]

# Land Registry type codes → human-readable
LR_TYPE_MAP = {'D': 'detached', 'S': 'semi-detached', 'T': 'terraced', 'F': 'flat'}


def _type_group(property_type: Optional[str]) -> str:
    """Map property_type string to a broad group for reception_rules."""
    if not property_type:
        return 'house'
    pt = property_type.lower()
    if 'flat' in pt or 'apartment' in pt or 'maisonette' in pt:
        return 'flat'
    if 'terrace' in pt:
        return 'terrace'
    return 'house'


def _sqm_to_sqft(sqm: float) -> float:
    return round(sqm * 10.764, 0)


def _sqm_to_acres(sqm: float) -> float:
    return round(sqm / 4046.86, 4)


# ---------------------------------------------------------------------------
# Main estimator class
# ---------------------------------------------------------------------------

class PropertyAttributeEstimator:
    """
    Orchestrates all attribute estimations for a property.

    Estimation priority (highest to lowest):
        1. User override
        2. Authoritative structured data (listing field, EPC)
        3. Land Registry / external structured data
        4. Listing text extraction (NLP)
        5. Heuristic rules (floor area + type bands)
        6. Unknown
    """

    def __init__(self, db: Session):
        self.db = db

    def estimate(self, prop: Property, overrides: Optional[dict] = None) -> dict:
        """
        Run the full estimation pipeline and return a structured result dict.

        Args:
            prop:      the Property ORM object
            overrides: dict of user-supplied field values (e.g. {'bedrooms': 4})

        Returns:
            {
                'profile': {field: AttributeField.to_dict(), ...},
                'source_summary': {key: value, ...},  # available facts
                'debug': {'warnings': [...], 'facts': {...}},
                'generated_at': ISO timestamp,
            }
        """
        overrides = overrides or {}
        facts = self._collect_facts(prop, overrides)
        debug: dict = {'facts': {k: v for k, v in facts.items() if k != 'description'},
                       'warnings': []}

        profile: dict[str, AttributeField] = {}
        profile['property_type']   = self._resolve_property_type(prop, facts, debug)
        profile['floor_area']      = self._resolve_floor_area(prop, facts, debug)
        profile['bedrooms']        = self._resolve_bedrooms(prop, facts, profile, debug)
        profile['bathrooms']       = self._resolve_bathrooms(prop, facts, profile, debug)
        profile['reception_rooms'] = self._resolve_reception_rooms(prop, facts, profile, debug)
        profile['plot_size']       = self._resolve_plot_size(prop, facts, debug)

        self._detect_contradictions(profile, debug)

        source_summary = {
            'has_floor_area':      'floor_area_sqm_listing' in facts or 'epc_floor_area_sqm' in facts,
            'has_epc':             'epc_floor_area_sqm' in facts or 'epc_property_type' in facts,
            'has_bedrooms':        'bedrooms_listing' in facts,
            'has_bathrooms':       'bathrooms_listing' in facts,
            'has_reception_rooms': 'reception_rooms_listing' in facts,
            'has_description':     'description' in facts,
            'has_lr_data':         'lr_property_type_dominant' in facts,
            'has_overrides':       bool(overrides),
            'override_fields':     list(overrides.keys()),
        }

        return {
            'profile': {k: v.to_dict() for k, v in profile.items()},
            'source_summary': source_summary,
            'debug': debug,
            'generated_at': datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Fact collection
    # ------------------------------------------------------------------

    def _collect_facts(self, prop: Property, overrides: dict) -> dict:
        """Gather all available input facts from property record and DB."""
        facts: dict = {}

        # Direct structured attributes
        if prop.property_type:
            facts['property_type_listing'] = prop.property_type
        if prop.bedrooms is not None:
            facts['bedrooms_listing'] = prop.bedrooms
        if prop.bathrooms is not None:
            facts['bathrooms_listing'] = prop.bathrooms
        if prop.reception_rooms is not None:
            facts['reception_rooms_listing'] = prop.reception_rooms
        if prop.floor_area_sqm is not None:
            facts['floor_area_sqm_listing'] = prop.floor_area_sqm
        if prop.plot_size_sqm is not None:
            facts['plot_size_sqm_listing'] = prop.plot_size_sqm
        if prop.description:
            facts['description'] = prop.description

        # EPC data — use cached values on Property if already matched,
        # otherwise do a live lookup (local DB table → API fallback)
        try:
            from backend.services import epc_service
            if prop.epc_matched_at is not None:
                # Already looked up — use cached values
                if prop.epc_floor_area_sqm is not None:
                    facts['epc_floor_area_sqm'] = prop.epc_floor_area_sqm
                if prop.epc_property_type:
                    facts['epc_property_type'] = prop.epc_property_type
            elif prop.postcode and prop.address:
                epc = epc_service.lookup_by_address(self.db, prop.postcode, prop.address)
                if epc:
                    if epc.get('floor_area_sqm') is not None:
                        facts['epc_floor_area_sqm'] = epc['floor_area_sqm']
                    if epc.get('mapped_type'):
                        facts['epc_property_type'] = epc['mapped_type']
                    # Cache results on the Property row to avoid re-querying
                    prop.epc_floor_area_sqm  = epc.get('floor_area_sqm')
                    prop.epc_property_type   = epc.get('mapped_type')
                    prop.epc_energy_rating   = epc.get('energy_rating')
                    prop.epc_inspection_date = epc.get('inspection_date')
                    prop.epc_matched_at      = datetime.utcnow()
                    self.db.flush()
                else:
                    # Mark as attempted (epc_matched_at = now, no data) so we
                    # don't retry on every estimation call
                    prop.epc_matched_at = datetime.utcnow()
                    self.db.flush()
        except Exception as e:
            logger.debug("EPC lookup failed for property %s: %s", getattr(prop, 'id', '?'), e)

        # Land Registry type inference from same postcode
        if prop.postcode:
            try:
                from backend.models.sales_history import SalesHistory
                lr_rows = (
                    self.db.query(SalesHistory.property_type)
                    .filter(SalesHistory.postcode == prop.postcode)
                    .limit(10)
                    .all()
                )
                lr_types = [r[0] for r in lr_rows if r[0]]
                if lr_types:
                    facts['lr_property_types'] = lr_types
                    facts['lr_property_type_dominant'] = Counter(lr_types).most_common(1)[0][0]
            except Exception as e:
                logger.debug('LR type lookup failed: %s', e)

        # NLP extraction from description
        if prop.description:
            facts.update(self._extract_from_description(prop.description))

        # User overrides are highest priority (stored with 'override_' prefix)
        for k, v in overrides.items():
            facts[f'override_{k}'] = v

        return facts

    def _extract_from_description(self, description: str) -> dict:
        """Extract structured hints from free-text listing description."""
        text = description.lower()
        extracted: dict = {}

        # Bedrooms
        m = re.search(r'(\d+)\s*bed(?:room)?s?', text)
        if m:
            extracted['bedrooms_text'] = int(m.group(1))

        # Bathrooms
        m = re.search(r'(\d+)\s*(?:bath(?:room)?s?|en.?suite)', text)
        if m:
            extracted['bathrooms_text'] = int(m.group(1))

        # Reception rooms — explicit count or keyword
        m = re.search(r'(\d+)\s*recep(?:tion)?\s*rooms?', text)
        if m:
            extracted['reception_rooms_text'] = int(m.group(1))
        elif 'three reception' in text:
            extracted['reception_rooms_text'] = 3
        elif 'two reception' in text or 'two living' in text:
            extracted['reception_rooms_text'] = 2

        # Floor area (sq ft mentioned → convert)
        m = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|sqft|ft²)', text)
        if m:
            sqft = float(m.group(1).replace(',', ''))
            extracted['floor_area_sqm_text'] = round(sqft * 0.0929, 1)

        # Property type keywords
        TYPE_KEYWORDS = [
            ('chalet bungalow', 'chalet bungalow'),
            ('end of terrace',  'end terrace'),
            ('end-of-terrace',  'end terrace'),
            ('end terrace',     'end terrace'),
            ('mid-terrace',     'mid terrace'),
            ('mid terrace',     'mid terrace'),
            ('semi-detached',   'semi-detached'),
            ('semi detached',   'semi-detached'),
            ('detached',        'detached'),
            ('terraced',        'terraced'),
            ('maisonette',      'maisonette'),
            ('bungalow',        'bungalow'),
            ('apartment',       'flat'),
            ('flat',            'flat'),
        ]
        for kw, pt in TYPE_KEYWORDS:
            if kw in text:
                extracted['property_type_text'] = pt
                break

        return extracted

    # ------------------------------------------------------------------
    # Per-attribute resolvers
    # ------------------------------------------------------------------

    def _resolve_property_type(self, prop, facts, debug) -> AttributeField:
        # 1. User override
        if 'override_property_type' in facts:
            return AttributeField(
                status='known', value=facts['override_property_type'],
                confidence=1.0, confidence_label='very_high',
                source='user_override', explanation='Manually confirmed by user.',
            )
        # 2. Structured listing data
        if 'property_type_listing' in facts:
            conf = 0.92
            return AttributeField(
                status='known', value=facts['property_type_listing'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing',
                explanation='Property type reported directly in listing data.',
            )
        # 2b. EPC certificate data
        if 'epc_property_type' in facts:
            conf = 0.92
            return AttributeField(
                status='known', value=facts['epc_property_type'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='epc',
                explanation='Property type derived from matched EPC certificate.',
            )
        # 3. Land Registry corroboration
        if 'lr_property_type_dominant' in facts:
            lr_code = facts['lr_property_type_dominant']
            mapped = LR_TYPE_MAP.get(lr_code)
            if mapped:
                conf = 0.83
                return AttributeField(
                    status='inferred', value=mapped,
                    confidence=conf, confidence_label=confidence_label(conf),
                    source='land_registry',
                    explanation=(
                        f'Inferred from Land Registry transaction type "{lr_code}" '
                        f'({len(facts.get("lr_property_types", []))} records at this postcode).'
                    ),
                )
        # 4. Description text
        if 'property_type_text' in facts:
            conf = 0.65
            return AttributeField(
                status='inferred', value=facts['property_type_text'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing_text',
                explanation='Inferred from keywords in the property description.',
            )
        return AttributeField.unknown('No property type data available.')

    def _resolve_floor_area(self, prop, facts, debug) -> AttributeField:
        # 1. User override
        if 'override_floor_area_sqm' in facts:
            sqm = float(facts['override_floor_area_sqm'])
            return AttributeField(
                status='known',
                value={'sqm': sqm, 'sqft': _sqm_to_sqft(sqm)},
                confidence=1.0, confidence_label='very_high',
                source='user_override', explanation='Manually confirmed by user.',
            )
        # 2. Structured listing data
        if 'floor_area_sqm_listing' in facts:
            sqm = facts['floor_area_sqm_listing']
            conf = 0.92
            return AttributeField(
                status='known',
                value={'sqm': sqm, 'sqft': _sqm_to_sqft(sqm)},
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing',
                explanation='Floor area reported directly in listing data.',
            )
        # 2b. EPC certificate data
        if 'epc_floor_area_sqm' in facts:
            sqm = facts['epc_floor_area_sqm']
            conf = 0.92
            return AttributeField(
                status='known',
                value={'sqm': sqm, 'sqft': _sqm_to_sqft(sqm)},
                confidence=conf, confidence_label=confidence_label(conf),
                source='epc',
                explanation='Floor area from matched EPC certificate (government register).',
            )
        # 3. Text extraction (sq ft → converted)
        if 'floor_area_sqm_text' in facts:
            sqm = facts['floor_area_sqm_text']
            conf = 0.70
            return AttributeField(
                status='inferred',
                value={'sqm': sqm, 'sqft': _sqm_to_sqft(sqm)},
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing_text',
                explanation='Floor area extracted from description text (converted from sq ft).',
            )
        return AttributeField.unknown('No floor area data available.')

    def _resolve_bedrooms(self, prop, facts, profile, debug) -> AttributeField:
        # 1. User override
        if 'override_bedrooms' in facts:
            beds = int(facts['override_bedrooms'])
            return AttributeField(
                status='known', value=beds,
                confidence=1.0, confidence_label='very_high',
                source='user_override', explanation='Manually confirmed by user.',
            )
        # 2. Structured listing data
        if 'bedrooms_listing' in facts:
            conf = 0.93
            return AttributeField(
                status='known', value=facts['bedrooms_listing'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing', explanation='Bedroom count reported in listing.',
            )
        # 3. Description text extraction
        if 'bedrooms_text' in facts:
            conf = 0.78
            return AttributeField(
                status='inferred', value=facts['bedrooms_text'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing_text',
                explanation='Bedroom count extracted from property description text.',
            )
        # 4. Floor area + type heuristic
        pt_field = profile.get('property_type')
        pt_val = pt_field.value if (pt_field and pt_field.status != 'unknown') else facts.get('property_type_listing')
        fa_field = profile.get('floor_area')
        sqm = None
        if fa_field and fa_field.status != 'unknown' and isinstance(fa_field.value, dict):
            sqm = fa_field.value.get('sqm')

        if sqm and pt_val:
            rules = BEDROOM_RULES.get(pt_val.lower())
            if rules is None:
                # Try partial key match (e.g. "end terrace" matches "end terrace")
                for key in BEDROOM_RULES:
                    if key in pt_val.lower():
                        rules = BEDROOM_RULES[key]
                        break
            if rules:
                for min_s, max_s, beds, conf in rules:
                    if min_s <= sqm < max_s:
                        return AttributeField(
                            status='estimated', value=beds,
                            confidence=conf, confidence_label=confidence_label(conf),
                            source='floor_area_heuristic',
                            explanation=(
                                f'Estimated from floor area ({sqm}m²) and property type ({pt_val}) '
                                'using floor area band rules for UK residential dwellings.'
                            ),
                        )

        return AttributeField.unknown('Insufficient data to estimate bedroom count.')

    def _resolve_bathrooms(self, prop, facts, profile, debug) -> AttributeField:
        # 1. User override
        if 'override_bathrooms' in facts:
            return AttributeField(
                status='known', value=int(facts['override_bathrooms']),
                confidence=1.0, confidence_label='very_high',
                source='user_override', explanation='Manually confirmed by user.',
            )
        # 2. Structured listing data
        if 'bathrooms_listing' in facts:
            conf = 0.90
            return AttributeField(
                status='known', value=facts['bathrooms_listing'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing', explanation='Bathroom count reported in listing.',
            )
        # 3. Description text extraction
        if 'bathrooms_text' in facts:
            conf = 0.72
            return AttributeField(
                status='inferred', value=facts['bathrooms_text'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing_text',
                explanation='Bathroom count extracted from property description.',
            )
        # 4. Bedroom-based heuristic
        beds_field = profile.get('bedrooms')
        beds = beds_field.value if (beds_field and beds_field.status != 'unknown') else None
        if beds is not None and isinstance(beds, int):
            for min_b, max_b, min_bath, max_bath, conf in BATHROOM_RULES:
                if min_b <= beds <= max_b:
                    # Reduce confidence if bedrooms were themselves estimated
                    if beds_field and beds_field.status == 'estimated':
                        conf = max(0.28, conf - 0.15)
                    if min_bath == max_bath:
                        value: Any = min_bath
                        expl = (
                            f'Estimated from bedroom count ({beds}) using typical UK '
                            'residential bathroom patterns.'
                        )
                    else:
                        value = {'min': min_bath, 'max': max_bath}
                        expl = (
                            f'Range estimate based on bedroom count ({beds}); '
                            'exact count not confirmed.'
                        )
                    return AttributeField(
                        status='estimated', value=value,
                        confidence=conf, confidence_label=confidence_label(conf),
                        source='bedroom_heuristic', explanation=expl,
                    )

        return AttributeField.unknown('Insufficient data to estimate bathroom count.')

    def _resolve_reception_rooms(self, prop, facts, profile, debug) -> AttributeField:
        # 1. User override
        if 'override_reception_rooms' in facts:
            return AttributeField(
                status='known', value=int(facts['override_reception_rooms']),
                confidence=1.0, confidence_label='very_high',
                source='user_override', explanation='Manually confirmed by user.',
            )
        # 2. Structured listing data
        if 'reception_rooms_listing' in facts:
            conf = 0.88
            return AttributeField(
                status='known', value=facts['reception_rooms_listing'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing', explanation='Reception room count reported in listing.',
            )
        # 3. Description text extraction
        if 'reception_rooms_text' in facts:
            conf = 0.70
            return AttributeField(
                status='inferred', value=facts['reception_rooms_text'],
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing_text',
                explanation='Reception room count extracted from property description.',
            )
        # 4. Type + bedroom heuristic
        pt_field = profile.get('property_type')
        pt_val = pt_field.value if (pt_field and pt_field.status != 'unknown') else None
        beds_field = profile.get('bedrooms')
        beds = beds_field.value if (beds_field and beds_field.status != 'unknown') else None

        if pt_val and beds is not None and isinstance(beds, int):
            tgroup = _type_group(pt_val)
            for tg, min_b, max_b, recep, conf in RECEPTION_RULES:
                if tg == tgroup and min_b <= beds <= max_b:
                    if beds_field and beds_field.status == 'estimated':
                        conf = max(0.28, conf - 0.12)
                    return AttributeField(
                        status='estimated', value=recep,
                        confidence=conf, confidence_label=confidence_label(conf),
                        source='type_bedroom_heuristic',
                        explanation=(
                            f'Estimated from property type ({pt_val}) and bedroom count ({beds}) '
                            'using typical UK dwelling layout patterns.'
                        ),
                    )

        return AttributeField.unknown('Insufficient data to estimate reception room count.')

    def _resolve_plot_size(self, prop, facts, debug) -> AttributeField:
        # 1. User override
        if 'override_plot_size_sqm' in facts:
            sqm = float(facts['override_plot_size_sqm'])
            return AttributeField(
                status='known',
                value={'sqm': sqm, 'sqft': _sqm_to_sqft(sqm), 'acres': _sqm_to_acres(sqm)},
                confidence=1.0, confidence_label='very_high',
                source='user_override', explanation='Manually confirmed by user.',
            )
        # 2. Structured listing data
        if 'plot_size_sqm_listing' in facts:
            sqm = facts['plot_size_sqm_listing']
            conf = 0.85
            return AttributeField(
                status='known',
                value={'sqm': sqm, 'sqft': _sqm_to_sqft(sqm), 'acres': _sqm_to_acres(sqm)},
                confidence=conf, confidence_label=confidence_label(conf),
                source='listing',
                explanation='Plot size reported in listing data.',
            )
        return AttributeField.unknown(
            'Plot size not available. Parcel geometry data not integrated in this version.'
        )

    # ------------------------------------------------------------------
    # Contradiction detection
    # ------------------------------------------------------------------

    def _detect_contradictions(self, profile: dict, debug: dict) -> None:
        """Flag impossible or suspicious combinations across estimated fields."""
        warnings = debug.setdefault('warnings', [])

        beds_field = profile.get('bedrooms')
        fa_field = profile.get('floor_area')

        if (beds_field and fa_field
                and beds_field.status != 'unknown'
                and fa_field.status != 'unknown'):
            beds = beds_field.value
            fa_val = fa_field.value
            sqm = fa_val.get('sqm', 0) if isinstance(fa_val, dict) else (fa_val or 0)

            if isinstance(beds, int) and sqm:
                if beds >= 5 and sqm < 80:
                    warnings.append(
                        f'{beds} bedrooms reported but floor area is only {sqm}m² — '
                        'typical 5-bed requires 140m²+. One or both values may be incorrect.'
                    )
                elif beds == 1 and sqm > 200:
                    warnings.append(
                        f'1 bedroom reported but floor area is {sqm}m² — unusually large '
                        'for a 1-bed. Possible misclassification or data error.'
                    )


# ---------------------------------------------------------------------------
# Merge helper: apply overrides on top of computed profile
# ---------------------------------------------------------------------------

def merge_profile(computed: dict, overrides: dict) -> dict:
    """
    Merge user overrides into a computed profile dict.

    For each field with an override, replace that field's AttributeField
    with a 'user_override' status entry and re-run dependent estimators
    by returning the merged profile (caller is responsible for recalculate).

    In practice we just return the computed result from estimate() which
    already treats override facts as highest-priority inputs.
    """
    return computed
