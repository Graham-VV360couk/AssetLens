"""Backfill EPC data onto properties that haven't been matched yet.
Matches by postcode + address against the 55M EPC bulk records.

Usage: docker exec -w /app backend-CONTAINER python scripts/backfill_epc.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.models.base import SessionLocal
from backend.models.property import Property
from backend.models.epc_certificate import EPCCertificate
from datetime import datetime

def run():
    db = SessionLocal()
    props = db.query(Property).filter(Property.epc_matched_at == None).all()
    matched = 0
    skipped = 0

    print(f"Found {len(props)} unmatched properties")

    for p in props:
        if not p.postcode:
            skipped += 1
            continue

        certs = (
            db.query(EPCCertificate)
            .filter(EPCCertificate.postcode == p.postcode)
            .order_by(EPCCertificate.inspection_date.desc())
            .limit(20)
            .all()
        )
        if not certs:
            skipped += 1
            continue

        best = None
        addr = p.address.lower() if p.address else ''
        for c in certs:
            ca = (c.address1 or '').lower()
            if addr and ca and (addr.split()[0] in ca or ca.split()[0] in addr):
                best = c
                break
        if not best:
            best = certs[0]

        p.epc_energy_rating = best.energy_rating
        p.epc_potential_rating = best.potential_energy_rating
        p.epc_floor_area_sqm = best.floor_area_sqm
        p.epc_property_type = best.property_type
        p.epc_inspection_date = best.inspection_date
        p.epc_matched_at = datetime.utcnow()

        if best.property_type and p.property_type in (None, 'unknown'):
            p.property_type = best.property_type.lower()
        if best.floor_area_sqm and not p.floor_area_sqm:
            p.floor_area_sqm = best.floor_area_sqm

        matched += 1
        if matched % 500 == 0:
            print(f"  {matched} matched...")

    db.commit()
    print(f"\nDone: {matched} matched, {skipped} skipped (no postcode or no EPC data)")
    db.close()

if __name__ == '__main__':
    print("EPC Backfill — matching properties to EPC certificates\n")
    run()
