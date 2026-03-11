"""
EPC Bulk Data Importer

Imports EPC certificates from the bulk download CSV files into the
epc_certificates table. Run once after downloading the bulk dataset.

Usage:
    python -m backend.etl.epc_importer --data-dir /path/to/expanded/epc/

The bulk download extracts to many CSVs — one per local authority — all with
the same column headers. This script discovers them via glob and imports in
10k-row chunks using efficient bulk INSERT with ON CONFLICT DO NOTHING.

Expected import time: ~15-30 minutes for ~24M records.
"""
import argparse
import glob
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd

from backend.models.base import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHUNK_SIZE = 10_000

# Map bulk CSV column names → model column names
COLUMN_MAP = {
    'LMK_KEY':               'lmk_key',
    'ADDRESS1':              'address1',
    'ADDRESS2':              'address2',
    'POSTCODE':              'postcode',
    'UPRN':                  'uprn',
    'PROPERTY_TYPE':         'property_type',
    'BUILT_FORM':            'built_form',
    'TOTAL_FLOOR_AREA':      'floor_area_sqm',
    'CURRENT_ENERGY_RATING': 'energy_rating',
    'INSPECTION_DATE':       'inspection_date',
}
KEEP_COLS = list(COLUMN_MAP.values())


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Rename, select, and type-cast columns."""
    # Rename only the columns we care about
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    # Keep only desired columns (drop any that don't exist)
    available = [c for c in KEEP_COLS if c in chunk.columns]
    chunk = chunk[available].copy()

    # Clean postcode: uppercase, strip
    if 'postcode' in chunk.columns:
        chunk['postcode'] = chunk['postcode'].astype(str).str.strip().str.upper()
        chunk = chunk[chunk['postcode'].str.len() > 0]

    # Normalise floor_area_sqm
    if 'floor_area_sqm' in chunk.columns:
        chunk['floor_area_sqm'] = pd.to_numeric(chunk['floor_area_sqm'], errors='coerce')

    # Normalise inspection_date
    if 'inspection_date' in chunk.columns:
        chunk['inspection_date'] = pd.to_datetime(
            chunk['inspection_date'], errors='coerce', format='%Y-%m-%d'
        ).dt.date

    # Drop rows missing lmk_key (can't upsert without it)
    if 'lmk_key' in chunk.columns:
        chunk = chunk.dropna(subset=['lmk_key'])
        chunk['lmk_key'] = chunk['lmk_key'].astype(str).str.strip()
        chunk = chunk[chunk['lmk_key'].str.len() > 0]

    # Replace NaN with None for correct SQL NULL insertion
    chunk = chunk.where(chunk.notna(), other=None)

    return chunk


def import_epc_bulk(data_dir: str, dry_run: bool = False) -> dict:
    """
    Import all EPC CSVs found under data_dir into the epc_certificates table.

    Returns:
        dict with keys: files_processed, rows_inserted, rows_skipped, errors
    """
    csv_files = sorted(glob.glob(f"{data_dir}/**/*.csv", recursive=True))
    if not csv_files:
        # Some bulk downloads use certificates.csv or certificates-*.csv at root level
        csv_files = sorted(glob.glob(f"{data_dir}/*.csv"))

    if not csv_files:
        logger.error("No CSV files found under %s", data_dir)
        return {'files_processed': 0, 'rows_inserted': 0, 'rows_skipped': 0, 'errors': 1}

    logger.info("Found %d CSV file(s) under %s", len(csv_files), data_dir)

    stats = {'files_processed': 0, 'rows_inserted': 0, 'rows_skipped': 0, 'errors': 0}
    db = SessionLocal()

    try:
        for file_idx, csv_path in enumerate(csv_files, 1):
            logger.info("[%d/%d] Processing %s", file_idx, len(csv_files), csv_path)
            try:
                chunk_iter = pd.read_csv(
                    csv_path,
                    chunksize=CHUNK_SIZE,
                    low_memory=False,
                    encoding='utf-8',
                    on_bad_lines='skip',
                )
                for chunk in chunk_iter:
                    cleaned = _clean_chunk(chunk)
                    if cleaned.empty:
                        continue

                    rows = cleaned.to_dict('records')
                    if dry_run:
                        stats['rows_inserted'] += len(rows)
                        continue

                    # Bulk insert using core INSERT ... ON CONFLICT DO NOTHING
                    # (avoids loading duplicates from re-runs)
                    inserted = _bulk_upsert(db, rows)
                    stats['rows_inserted'] += inserted
                    stats['rows_skipped'] += len(rows) - inserted

                stats['files_processed'] += 1
                db.commit()
                logger.info(
                    "  → %d rows inserted so far (total)", stats['rows_inserted']
                )

            except Exception as e:
                logger.error("Error processing %s: %s", csv_path, e)
                stats['errors'] += 1
                db.rollback()
                continue

    finally:
        db.close()

    logger.info(
        "Import complete: %d files, %d inserted, %d skipped, %d errors",
        stats['files_processed'],
        stats['rows_inserted'],
        stats['rows_skipped'],
        stats['errors'],
    )
    return stats


def _bulk_upsert(db, rows: list) -> int:
    """
    Insert rows into epc_certificates, skipping duplicates by lmk_key.
    Returns number of rows actually inserted.
    """
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


def main():
    parser = argparse.ArgumentParser(description='Import EPC bulk CSV data into epc_certificates table')
    parser.add_argument('--data-dir', required=True, help='Path to expanded EPC bulk download directory')
    parser.add_argument('--dry-run', action='store_true', help='Parse and count rows without inserting')
    args = parser.parse_args()

    import_epc_bulk(args.data_dir, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
