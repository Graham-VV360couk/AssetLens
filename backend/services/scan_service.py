"""
On-demand property scan service.
Orchestrates lookups across Land Registry, EPC, PropertyData, and scoring
to build a full intelligence profile for any UK address.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from backend.models.property import Property, PropertySource, PropertyScore
from backend.models.sales_history import SalesHistory
from backend.models.epc_certificate import EPCCertificate
from backend.services.deduplication_service import PropertyDeduplicator
from backend.services.scoring_service import PropertyScoringService
from backend.services.propertydata_service import PropertyDataService

logger = logging.getLogger(__name__)

STALE_DAYS = 7


class ScanService:
    def __init__(self, db: Session):
        self.db = db
        self.deduplicator = PropertyDeduplicator(db)
        self.scoring = PropertyScoringService(db)
        self.pd_service = PropertyDataService()

    def scan(self, address: str, postcode: str) -> Dict[str, Any]:
        """
        Scan a property by address + postcode. Returns full intelligence profile.
        - If property exists in DB and is fresh, returns cached data.
        - If postcode only (no address), returns area-level data.
        - Otherwise creates property, enriches, scores, and returns.
        """
        postcode = (postcode or '').strip().upper()
        address = (address or '').strip()

        if not postcode:
            raise ValueError("Postcode is required")

        # Postcode-only: area scan
        if not address or len(address) < 5:
            area_data = self._area_scan(postcode)
            return {
                'scan_type': 'area',
                'postcode': postcode,
                'cached': False,
                **area_data,
            }

        # Check for existing property
        existing = self._find_existing(address, postcode)
        if existing:
            return self._build_response(existing, cached=True)

        # Create new property from scan
        prop = self._create_scanned_property(address, postcode)
        self._enrich_property(prop)
        self._score_property(prop)

        self.db.commit()
        return self._build_response(prop, cached=False)

    def _find_existing(self, address: str, postcode: str) -> Optional[Property]:
        """Check if property already exists via dedup. Returns None if not found or stale."""
        match = self.deduplicator.find_duplicate(address=address, postcode=postcode)
        if match:
            # Check staleness — re-enrich if older than STALE_DAYS
            if match.updated_at and match.updated_at < datetime.utcnow() - timedelta(days=STALE_DAYS):
                self._enrich_property(match)
                self._score_property(match)
                self.db.commit()
            return match
        return None

    def _area_scan(self, postcode: str) -> Dict[str, Any]:
        """Return area-level data when no specific address is available."""
        district = postcode.split()[0] if ' ' in postcode else postcode[:-3].strip()

        # Sales history for the postcode district
        sales = (
            self.db.query(SalesHistory)
            .filter(SalesHistory.postcode.ilike(f'{district}%'))
            .order_by(SalesHistory.sale_date.desc())
            .limit(50)
            .all()
        )

        prices = [s.sale_price for s in sales if s.sale_price]
        avg_price = sum(prices) / len(prices) if prices else None

        return {
            'district': district,
            'avg_price': avg_price,
            'recent_sales_count': len(sales),
            'sales_history': [
                {'date': str(s.sale_date), 'price': s.sale_price, 'address': s.address}
                for s in sales[:20]
            ],
        }

    def _create_scanned_property(self, address: str, postcode: str) -> Property:
        """Create a new property record from an on-demand scan."""
        # Look up EPC data for this address
        epc = self._find_epc(address, postcode)

        prop = Property(
            address=address,
            postcode=postcode,
            property_type=epc.property_type.lower() if epc and epc.property_type else 'unknown',
            status='active',
            date_found=datetime.utcnow(),
        )

        if epc:
            prop.epc_energy_rating = epc.energy_rating
            prop.epc_potential_rating = epc.potential_energy_rating
            prop.epc_floor_area_sqm = epc.floor_area_sqm
            prop.epc_property_type = epc.property_type
            prop.epc_inspection_date = epc.inspection_date
            prop.epc_matched_at = datetime.utcnow()

        self.db.add(prop)
        self.db.flush()

        # Add source record
        self.deduplicator.add_property_source(
            prop.id,
            source_name='on_demand_scan',
            source_id=None,
            source_url=None,
        )

        return prop

    def _find_epc(self, address: str, postcode: str) -> Optional[EPCCertificate]:
        """Find best EPC certificate match for an address."""
        certs = (
            self.db.query(EPCCertificate)
            .filter(EPCCertificate.postcode == postcode)
            .order_by(EPCCertificate.inspection_date.desc())
            .limit(20)
            .all()
        )
        if not certs:
            return None

        # Simple address matching — first token match
        addr_lower = address.lower()
        for cert in certs:
            cert_addr = (cert.address1 or '').lower()
            if addr_lower.split()[0] in cert_addr or cert_addr.split()[0] in addr_lower:
                return cert

        # Fall back to most recent for this postcode
        return certs[0] if certs else None

    def _enrich_property(self, prop: Property):
        """Enrich with PropertyData AVM, rental estimate, flood risk."""
        try:
            score = self.db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()
            if not score:
                score = PropertyScore(property_id=prop.id)
                self.db.add(score)
                self.db.flush()
            self.pd_service.enrich(prop, score, self.db)
        except Exception as e:
            logger.warning("PropertyData enrichment failed for %d: %s", prop.id, e)

    def _score_property(self, prop: Property):
        """Run the scoring service on the property."""
        try:
            self.scoring.score_property(prop)
        except Exception as e:
            logger.warning("Scoring failed for %d: %s", prop.id, e)

    def _build_response(self, prop: Property, cached: bool) -> Dict[str, Any]:
        """Build the scan response dict from a property record."""
        score = self.db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()

        return {
            'scan_type': 'property',
            'cached': cached,
            'property_id': prop.id,
            'address': prop.address,
            'postcode': prop.postcode,
            'property_type': prop.property_type,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'asking_price': prop.asking_price,
            'epc_rating': prop.epc_energy_rating,
            'epc_potential_rating': prop.epc_potential_rating,
            'epc_floor_area': prop.epc_floor_area_sqm,
            'score': {
                'investment_score': score.investment_score if score else None,
                'price_band': score.price_band if score else None,
                'estimated_value': score.estimated_value if score else None,
                'gross_yield_pct': score.gross_yield_pct if score else None,
                'pd_avm': score.pd_avm if score else None,
                'pd_rental_estimate': score.pd_rental_estimate if score else None,
                'pd_flood_risk': score.pd_flood_risk if score else None,
            } if score else None,
        }
