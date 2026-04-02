"""
EPC Bulk Data Importer

Imports EPC certificates and (optionally) improvement recommendations from the
bulk download CSV files into epc_certificates and epc_recommendations tables.

Usage:
    # Certificates only (default)
    python -m backend.etl.epc_importer --data-dir /path/to/expanded/epc/

    # Certificates + recommendations
    python -m backend.etl.epc_importer --data-dir /path/to/expanded/epc/ --include-recommendations

The bulk download extracts to many CSVs -- one per local authority -- all with
the same column headers. This script discovers them via glob and imports in
10k-row chunks using efficient bulk INSERT with ON CONFLICT DO NOTHING.

Expected import time: ~15-30 minutes for ~24M records.
"""
import argparse
import glob
import logging
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd

from backend.models.base import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHUNK_SIZE = 10_000

# Map bulk CSV column names -> model column names (certificates)
CERT_COLUMN_MAP = {
    'LMK_KEY':                      'lmk_key',
    'ADDRESS1':                     'address1',
    'ADDRESS2':                     'address2',
    'POSTCODE':                     'postcode',
    'UPRN':                         'uprn',
    'PROPERTY_TYPE':                'property_type',
    'BUILT_FORM':                   'built_form',
    'TOTAL_FLOOR_AREA':             'floor_area_sqm',
    'CURRENT_ENERGY_RATING':        'energy_rating',
    'POTENTIAL_ENERGY_RATING':      'potential_energy_rating',
    'INSPECTION_DATE':              'inspection_date',
    # Extended Tier 1 fields
    'CONSTRUCTION_AGE_BAND':        'construction_age_band',
    'CURRENT_ENERGY_EFFICIENCY':    'current_energy_efficiency',
    'POTENTIAL_ENERGY_EFFICIENCY':  'potential_energy_efficiency',
    'TENURE':                       'tenure',
    'MAINS_GAS_FLAG':               'mains_gas_flag',
    'HEATING_COST_CURRENT':         'heating_cost_current',
    'HEATING_COST_POTENTIAL':       'heating_cost_potential',
    'HOT_WATER_COST_CURRENT':       'hot_water_cost_current',
    'HOT_WATER_COST_POTENTIAL':     'hot_water_cost_potential',
    'LIGHTING_COST_CURRENT':        'lighting_cost_current',
    'LIGHTING_COST_POTENTIAL':      'lighting_cost_potential',
    'CO2_EMISSIONS_CURRENT':        'co2_emissions_current',
    'NUMBER_HABITABLE_ROOMS':       'number_habitable_rooms',
    'TRANSACTION_TYPE':             'transaction_type',
}
CERT_KEEP = list(CERT_COLUMN_MAP.values())

# Map bulk CSV column names -> model column names (recommendations)
REC_COLUMN_MAP = {
    'LMK_KEY':                      'lmk_key',
    'IMPROVEMENT_ITEM':             'improvement_item',
    'IMPROVEMENT_SUMMARY_TEXT':     'improvement_summary_text',
    'IMPROVEMENT_DESCR_TEXT':       'improvement_descr_text',
    'INDICATIVE_COST':              'indicative_cost_raw',
    # Extended fields
    'TYPICAL_SAVING':               'typical_saving',
    'ENERGY_EFFICIENCY_RATING_A':   'efficiency_rating_before',
    'ENERGY_EFFICIENCY_RATING_B':   'efficiency_rating_after',
}
REC_KEEP = list(REC_COLUMN_MAP.values())

# EPC ratings in ascending order of energy performance
EPC_RATING_ORDER = ['G', 'F', 'E', 'D', 'C', 'B', 'A']
# Properties must be at least EPC E to be rented legally (England & Wales)
MIN_LETTABLE_RATING = 'E'


def _parse_cost_range(raw: str):
    """
    Parse a cost string like '£500 - £1,500' into (low, high) integers.
    Returns (None, None) if unparseable.
    """
    if not raw or not isinstance(raw, str):
        return None, None
    nums = re.findall(r'[\d,]+', raw.replace(',', ''))
    # re.findall with commas stripped
    nums = re.findall(r'\d+', raw.replace(',', ''))
    if len(nums) >= 2:
        return int(nums[0]), int(nums[-1])
    elif len(nums) == 1:
        v = int(nums[0])
        return v, v
    return None, None


def _clean_cert_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Rename, select, and type-cast certificate columns."""
    rename_map = {k: v for k, v in CERT_COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    available = [c for c in CERT_KEEP if c in chunk.columns]
    chunk = chunk[available].copy()

    if 'postcode' in chunk.columns:
        chunk['postcode'] = chunk['postcode'].astype(str).str.strip().str.upper()
        chunk = chunk[chunk['postcode'].str.len() > 0]

    if 'floor_area_sqm' in chunk.columns:
        chunk['floor_area_sqm'] = pd.to_numeric(chunk['floor_area_sqm'], errors='coerce')

    if 'inspection_date' in chunk.columns:
        chunk['inspection_date'] = pd.to_datetime(
            chunk['inspection_date'], errors='coerce', format='%Y-%m-%d'
        ).dt.date

    if 'lmk_key' in chunk.columns:
        chunk = chunk.dropna(subset=['lmk_key'])
        chunk['lmk_key'] = chunk['lmk_key'].astype(str).str.strip()
        chunk = chunk[chunk['lmk_key'].str.len() > 0]

    str_limits = {
        'lmk_key': 100, 'address1': 200, 'address2': 200,
        'postcode': 10, 'uprn': 20, 'property_type': 50,
        'built_form': 50, 'energy_rating': 5, 'potential_energy_rating': 5,
    }
    for col, limit in str_limits.items():
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str[:limit]

    # Compute EPC expiry date (inspection_date + 10 years)
    if 'inspection_date' in chunk.columns and chunk['inspection_date'].notna().any():
        chunk['epc_expiry_date'] = pd.to_datetime(chunk['inspection_date'], errors='coerce') + pd.DateOffset(years=10)
        chunk['epc_expiry_date'] = chunk['epc_expiry_date'].dt.date

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _clean_rec_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Rename, select, parse, and clean recommendation columns."""
    rename_map = {k: v for k, v in REC_COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    available = [c for c in REC_KEEP if c in chunk.columns]
    chunk = chunk[available].copy()

    if 'lmk_key' in chunk.columns:
        chunk = chunk.dropna(subset=['lmk_key'])
        chunk['lmk_key'] = chunk['lmk_key'].astype(str).str.strip()
        chunk = chunk[chunk['lmk_key'].str.len() > 0]

    # Parse cost range into low/high
    if 'indicative_cost_raw' in chunk.columns:
        costs = chunk['indicative_cost_raw'].apply(
            lambda v: pd.Series(_parse_cost_range(v), index=['indicative_cost_low', 'indicative_cost_high'])
        )
        chunk['indicative_cost_low'] = costs['indicative_cost_low'].astype('Int64')
        chunk['indicative_cost_high'] = costs['indicative_cost_high'].astype('Int64')
        # Convert Int64 nulls to Python None for SQLAlchemy
        chunk['indicative_cost_low'] = chunk['indicative_cost_low'].where(
            chunk['indicative_cost_low'].notna(), other=None
        )
        chunk['indicative_cost_high'] = chunk['indicative_cost_high'].where(
            chunk['indicative_cost_high'].notna(), other=None
        )

    str_limits = {
        'lmk_key': 100, 'improvement_item': 100,
        'improvement_summary_text': 500, 'indicative_cost_raw': 100,
    }
    for col, limit in str_limits.items():
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str[:limit]

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _bulk_upsert_certs(db, rows: list) -> int:
    """Insert certificate rows, skipping duplicates by lmk_key."""
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.epc_certificate import EPCCertificate

    now = datetime.utcnow()
    for row in rows:
        row.setdefault('created_at', now)
        row.setdefault('updated_at', now)

    stmt = pg_insert(EPCCertificate.__table__).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=['lmk_key'])
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def _bulk_insert_recs(db, rows: list) -> int:
    """Bulk insert recommendation rows, skipping duplicates by (lmk_key, improvement_item)."""
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.epc_recommendation import EPCRecommendation

    now = datetime.utcnow()
    for row in rows:
        row['created_at'] = row.get('created_at') or now
        row['updated_at'] = row.get('updated_at') or now

    stmt = pg_insert(EPCRecommendation.__table__).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint='uq_epc_rec_lmk_key_item')
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def _import_csv_files(db, csv_files: list, chunk_cleaner, bulk_inserter, label: str, dry_run: bool) -> dict:
    """Generic CSV import loop used for both certificates and recommendations."""
    stats = {'files_processed': 0, 'rows_inserted': 0, 'rows_skipped': 0, 'errors': 0}

    for file_idx, csv_path in enumerate(csv_files, 1):
        logger.info("[%d/%d] Processing %s (%s)", file_idx, len(csv_files), csv_path, label)
        try:
            chunk_iter = pd.read_csv(
                csv_path,
                chunksize=CHUNK_SIZE,
                low_memory=False,
                encoding='utf-8',
                on_bad_lines='skip',
            )
            for chunk in chunk_iter:
                try:
                    cleaned = chunk_cleaner(chunk)
                    if cleaned.empty:
                        continue
                    rows = cleaned.to_dict('records')
                    if dry_run:
                        stats['rows_inserted'] += len(rows)
                        continue
                except Exception as ce:
                    logger.warning("Chunk clean error in %s: %s", csv_path, ce)
                    stats['errors'] += 1
                    continue

                try:
                    inserted = bulk_inserter(db, rows)
                    stats['rows_inserted'] += inserted
                    stats['rows_skipped'] += len(rows) - inserted
                except Exception as ue:
                    logger.warning("Insert error in %s (chunk skipped): %s", csv_path, ue)
                    stats['errors'] += 1
                    db.rollback()

            stats['files_processed'] += 1
            db.commit()
            logger.info("  -> %d rows inserted so far (total)", stats['rows_inserted'])

        except Exception as e:
            logger.error("Error processing %s: %s", csv_path, e)
            stats['errors'] += 1
            db.rollback()

    return stats


def import_epc_bulk(data_dir: str, dry_run: bool = False, include_recommendations: bool = False) -> dict:
    """
    Import all EPC CSVs found under data_dir into the epc_certificates table.
    If include_recommendations=True, also imports recommendations.csv files.
    """
    # Find certificate CSVs (named 'certificates.csv' or matching certificates*.csv)
    cert_files = sorted(glob.glob(f"{data_dir}/**/certificates.csv", recursive=True))
    if not cert_files:
        cert_files = sorted(glob.glob(f"{data_dir}/**/*.csv", recursive=True))
    if not cert_files:
        cert_files = sorted(glob.glob(f"{data_dir}/*.csv"))

    if not cert_files:
        logger.error("No certificate CSV files found under %s", data_dir)
        return {'files_processed': 0, 'rows_inserted': 0, 'rows_skipped': 0, 'errors': 1}

    logger.info("Found %d certificate CSV file(s) under %s", len(cert_files), data_dir)

    db = SessionLocal()
    try:
        cert_stats = _import_csv_files(
            db, cert_files, _clean_cert_chunk, _bulk_upsert_certs,
            label='certificates', dry_run=dry_run,
        )
        logger.info(
            "Certificates complete: %d files, %d inserted, %d skipped, %d errors",
            cert_stats['files_processed'], cert_stats['rows_inserted'],
            cert_stats['rows_skipped'], cert_stats['errors'],
        )

        rec_stats = {'files_processed': 0, 'rows_inserted': 0, 'rows_skipped': 0, 'errors': 0}
        if include_recommendations:
            rec_files = sorted(glob.glob(f"{data_dir}/**/recommendations.csv", recursive=True))
            if not rec_files:
                logger.warning("No recommendations.csv files found under %s", data_dir)
            else:
                logger.info("Found %d recommendations.csv file(s)", len(rec_files))
                rec_stats = _import_csv_files(
                    db, rec_files, _clean_rec_chunk, _bulk_insert_recs,
                    label='recommendations', dry_run=dry_run,
                )
                logger.info(
                    "Recommendations complete: %d files, %d inserted, %d errors",
                    rec_stats['files_processed'], rec_stats['rows_inserted'], rec_stats['errors'],
                )

        return {
            'cert_files': cert_stats['files_processed'],
            'cert_inserted': cert_stats['rows_inserted'],
            'cert_skipped': cert_stats['rows_skipped'],
            'cert_errors': cert_stats['errors'],
            'rec_files': rec_stats['files_processed'],
            'rec_inserted': rec_stats['rows_inserted'],
            'rec_errors': rec_stats['errors'],
        }

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Import EPC bulk CSV data')
    parser.add_argument('--data-dir', required=True, help='Path to expanded EPC bulk download directory')
    parser.add_argument('--dry-run', action='store_true', help='Parse and count rows without inserting')
    parser.add_argument('--include-recommendations', action='store_true',
                        help='Also import recommendations.csv files into epc_recommendations table')
    args = parser.parse_args()

    import_epc_bulk(
        args.data_dir,
        dry_run=args.dry_run,
        include_recommendations=args.include_recommendations,
    )


if __name__ == '__main__':
    main()
