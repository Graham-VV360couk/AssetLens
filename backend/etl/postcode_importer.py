"""
ONS Postcode Directory (ONSPD) Importer

Imports the ONSPD CSV into the postcodes table — the glue that links
postcodes to LSOA, MSOA, IMD, coordinates, and all geographic hierarchies.

Usage:
    python -m backend.etl.postcode_importer --csv-file tmp/ONSPD_FEB_2025_UK.csv
    python -m backend.etl.postcode_importer --csv-file tmp/ONSPD_FEB_2025_UK.csv --dry-run
"""
import argparse
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd

from backend.models.base import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1_000

COLUMN_MAP = {
    'pcds':      'postcode',
    'dointr':    'date_introduced',
    'doterm':    'date_terminated',
    'lat':       'latitude',
    'long':      'longitude',
    'oseast1m':  'easting',
    'osnrth1m':  'northing',
    'osgrdind':  'grid_quality',
    'oslaua':    'lad_code',
    'osward':    'ward_code',
    'oscty':     'county_code',
    'rgn':       'region_code',
    'ctry':      'country_code',
    'pcon':      'pcon_code',
    'parish':    'parish_code',
    'oa21':      'oa21_code',
    'lsoa11':    'lsoa11_code',
    'lsoa21':    'lsoa21_code',
    'msoa11':    'msoa11_code',
    'msoa21':    'msoa21_code',
    'imd':       'imd_rank',
    'ru11ind':   'rural_urban',
    'oac11':     'oac11',
    'pfa':       'pfa_code',
    'icb':       'icb_code',
}

KEEP_COLUMNS = list(COLUMN_MAP.values())


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Rename, select, and type-cast ONSPD columns."""
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    available = [c for c in KEEP_COLUMNS if c in chunk.columns]
    chunk = chunk[available].copy()

    # Postcode is required
    if 'postcode' not in chunk.columns:
        return pd.DataFrame()
    chunk['postcode'] = chunk['postcode'].astype(str).str.strip()
    chunk = chunk[chunk['postcode'].str.len() > 0]
    chunk = chunk[chunk['postcode'] != 'nan']

    # Coordinates
    for col in ('latitude', 'longitude'):
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
            # Filter out sentinel values (99.999999 = no coords)
            if col == 'latitude':
                chunk.loc[chunk[col] > 90, col] = None
            if col == 'longitude':
                chunk.loc[chunk[col].abs() > 180, col] = None

    # Integer columns — use nullable Int64
    for col in ('easting', 'northing', 'grid_quality', 'imd_rank'):
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce').astype('Int64')
            # IMD 0 means no data
            if col == 'imd_rank':
                chunk.loc[chunk[col] == 0, col] = pd.NA

    # Date fields — strip trailing .0 from float conversion
    for col in ('date_introduced', 'date_terminated'):
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str.replace(r'\.0$', '', regex=True)

    # String columns — clean nulls
    str_cols = [
        'date_introduced', 'date_terminated', 'lad_code', 'ward_code',
        'county_code', 'region_code', 'country_code', 'pcon_code',
        'parish_code', 'oa21_code', 'lsoa11_code', 'lsoa21_code',
        'msoa11_code', 'msoa21_code', 'rural_urban', 'oac11',
        'pfa_code', 'icb_code',
    ]
    for col in str_cols:
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str.strip()
            chunk.loc[chunk[col].isin(['', 'nan', 'None']), col] = None

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _bulk_upsert(db, rows: list) -> int:
    """Insert postcode rows, updating on conflict."""
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.postcode import Postcode

    now = datetime.utcnow()
    for row in rows:
        row.setdefault('created_at', now)
        row.setdefault('updated_at', now)

    stmt = pg_insert(Postcode.__table__).values(rows)
    update_cols = {c.name: c for c in stmt.excluded if c.name not in ('id', 'postcode', 'created_at')}
    stmt = stmt.on_conflict_do_update(
        index_elements=['postcode'],
        set_=update_cols,
    )
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def import_postcodes(csv_file: str, dry_run: bool = False) -> dict:
    """Import ONSPD CSV into the postcodes table."""
    logger.info("Reading %s", csv_file)

    stats = {'rows_inserted': 0, 'rows_skipped': 0, 'errors': 0}
    db = SessionLocal()

    try:
        chunk_iter = pd.read_csv(
            csv_file,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding='utf-8',
            on_bad_lines='skip',
        )

        for chunk_num, chunk in enumerate(chunk_iter, 1):
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

                if chunk_num % 25 == 0 or chunk_num == 1:
                    logger.info("Chunk %d: %d rows cleaned (%d total so far)",
                                chunk_num, len(rows), stats['rows_inserted'])

                if dry_run:
                    stats['rows_inserted'] += len(rows)
                    continue

                inserted = _bulk_upsert(db, rows)
                stats['rows_inserted'] += inserted
                stats['rows_skipped'] += len(rows) - inserted
                db.commit()

            except Exception as e:
                logger.warning("Chunk %d error: %s", chunk_num, e)
                stats['errors'] += 1
                db.rollback()

        logger.info(
            "Import complete: %d upserted, %d skipped, %d errors",
            stats['rows_inserted'], stats['rows_skipped'], stats['errors'],
        )
        return stats

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Import ONS Postcode Directory CSV')
    parser.add_argument('--csv-file', required=True, help='Path to ONSPD CSV file')
    parser.add_argument('--dry-run', action='store_true', help='Parse and count without inserting')
    args = parser.parse_args()

    import_postcodes(args.csv_file, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
