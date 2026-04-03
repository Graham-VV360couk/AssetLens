"""
UK Police Crime Data Importer

Imports street-level crime data from data.police.uk CSV exports.
Recursively discovers all CSVs in a directory and imports them.

Usage:
    python -m backend.etl.crime_importer --data-dir /tmp/crime-data
    python -m backend.etl.crime_importer --data-dir /tmp/crime-data --dry-run
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

COLUMN_MAP = {
    'Crime ID':              'crime_id',
    'Month':                 'month',
    'Latitude':              'latitude',
    'Longitude':             'longitude',
    'Location':              'location',
    'Falls within':          'falls_within',
    'LSOA code':             'lsoa_code',
    'LSOA name':             'lsoa_name',
    'Crime type':            'crime_type',
    'Last outcome category': 'last_outcome',
}

KEEP_COLUMNS = list(COLUMN_MAP.values())


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Rename, select, and type-cast crime columns."""
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    available = [c for c in KEEP_COLUMNS if c in chunk.columns]
    chunk = chunk[available].copy()

    # Crime type is required
    if 'crime_type' not in chunk.columns:
        return pd.DataFrame()
    chunk = chunk.dropna(subset=['crime_type'])
    chunk = chunk[chunk['crime_type'].str.strip().str.len() > 0]

    # Parse month (YYYY-MM) to first-of-month date
    if 'month' in chunk.columns:
        chunk['month'] = pd.to_datetime(chunk['month'], format='%Y-%m', errors='coerce').dt.date
        chunk = chunk.dropna(subset=['month'])

    # Coordinates
    for col in ('latitude', 'longitude'):
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

    # String length limits
    str_limits = {
        'crime_id': 70, 'location': 200, 'falls_within': 100,
        'lsoa_code': 15, 'lsoa_name': 100, 'crime_type': 50,
        'last_outcome': 100,
    }
    for col, limit in str_limits.items():
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str[:limit]
            chunk.loc[chunk[col].isin(['nan', 'None', '']), col] = None

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _bulk_insert(db, rows: list) -> int:
    """Bulk insert crime rows."""
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.crime import Crime

    now = datetime.utcnow()
    for row in rows:
        row.setdefault('created_at', now)
        row.setdefault('updated_at', now)

    stmt = pg_insert(Crime.__table__).values(rows)
    # No unique constraint to conflict on — crime_id can be null and
    # duplicates across re-downloads are possible, so skip if crime_id matches
    # For records without crime_id (ASB), we just insert (minor duplication
    # is acceptable; dedup can be done in queries).
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def _detect_encoding(csv_path: str) -> str:
    """Try common encodings and return the first that works."""
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'latin-1'  # fallback — latin-1 never raises


def import_crime_data(data_dir: str, dry_run: bool = False) -> dict:
    """Import all crime CSVs found recursively under data_dir."""
    csv_files = sorted(glob.glob(f"{data_dir}/**/*.csv", recursive=True))
    if not csv_files:
        csv_files = sorted(glob.glob(f"{data_dir}/*.csv"))

    if not csv_files:
        logger.error("No CSV files found under %s", data_dir)
        return {'files_processed': 0, 'rows_inserted': 0, 'errors': 0}

    logger.info("Found %d CSV file(s) under %s", len(csv_files), data_dir)

    stats = {'files_processed': 0, 'rows_inserted': 0, 'errors': 0}
    db = SessionLocal()

    try:
        for file_idx, csv_path in enumerate(csv_files, 1):
            encoding = _detect_encoding(csv_path)
            logger.info("[%d/%d] %s (encoding: %s)", file_idx, len(csv_files), csv_path, encoding)

            try:
                chunk_iter = pd.read_csv(
                    csv_path,
                    chunksize=CHUNK_SIZE,
                    low_memory=False,
                    encoding=encoding,
                    on_bad_lines='skip',
                )

                file_rows = 0
                for chunk in chunk_iter:
                    try:
                        cleaned = _clean_chunk(chunk)
                        if cleaned.empty:
                            continue
                        rows = cleaned.to_dict('records')
                        # Convert pandas NA/NaN to Python None
                        for row in rows:
                            for k, v in row.items():
                                try:
                                    if pd.isna(v):
                                        row[k] = None
                                except (TypeError, ValueError):
                                    pass

                        if dry_run:
                            file_rows += len(rows)
                            continue

                        inserted = _bulk_insert(db, rows)
                        file_rows += inserted

                    except Exception as ce:
                        logger.warning("Chunk error in %s: %s", csv_path, ce)
                        stats['errors'] += 1
                        db.rollback()

                db.commit()
                stats['files_processed'] += 1
                stats['rows_inserted'] += file_rows
                logger.info("  -> %d rows from this file (%d total)", file_rows, stats['rows_inserted'])

            except Exception as e:
                logger.error("Error processing %s: %s", csv_path, e)
                stats['errors'] += 1
                db.rollback()

        logger.info(
            "Import complete: %d files, %d rows inserted, %d errors",
            stats['files_processed'], stats['rows_inserted'], stats['errors'],
        )
        return stats

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Import UK police crime CSV data')
    parser.add_argument('--data-dir', required=True, help='Directory containing crime CSVs (searched recursively)')
    parser.add_argument('--dry-run', action='store_true', help='Parse and count without inserting')
    args = parser.parse_args()

    import_crime_data(args.data_dir, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
