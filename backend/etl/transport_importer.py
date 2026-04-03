"""
NaPTAN Transport Stops Importer

Imports public transport stops from the NaPTAN Stops.csv file.

Usage:
    python -m backend.etl.transport_importer --csv-file tmp/Stops.csv
    python -m backend.etl.transport_importer --csv-file tmp/Stops.csv --dry-run
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

CHUNK_SIZE = 2_000

COLUMN_MAP = {
    'ATCOCode':         'atco_code',
    'CommonName':       'name',
    'Street':           'street',
    'LocalityName':     'locality_name',
    'Town':             'town',
    'StopType':         'stop_type',
    'BusStopType':      'bus_stop_type',
    'Bearing':          'bearing',
    'Latitude':         'latitude',
    'Longitude':        'longitude',
    'Easting':          'easting',
    'Northing':         'northing',
    'Status':           'status',
}

KEEP_COLUMNS = list(COLUMN_MAP.values())


def _detect_encoding(csv_path: str) -> str:
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'latin-1'


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    available = [c for c in KEEP_COLUMNS if c in chunk.columns]
    chunk = chunk[available].copy()

    # ATCOCode and name are required
    if 'atco_code' not in chunk.columns or 'name' not in chunk.columns:
        return pd.DataFrame()
    chunk = chunk.dropna(subset=['atco_code', 'name'])
    chunk['atco_code'] = chunk['atco_code'].astype(str).str.strip()
    chunk = chunk[chunk['atco_code'].str.len() > 0]

    # Coordinates
    for col in ('latitude', 'longitude'):
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

    # Integer columns
    for col in ('easting', 'northing'):
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce').astype('Int64')

    # String limits
    str_limits = {
        'atco_code': 20, 'name': 200, 'street': 200,
        'locality_name': 100, 'town': 100, 'stop_type': 10,
        'bus_stop_type': 10, 'bearing': 5, 'status': 10,
    }
    for col, limit in str_limits.items():
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str[:limit]
            chunk.loc[chunk[col].isin(['nan', 'None', '']), col] = None

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _bulk_upsert(db, rows: list) -> int:
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.transport_stop import TransportStop

    now = datetime.utcnow()
    for row in rows:
        row.setdefault('created_at', now)
        row.setdefault('updated_at', now)

    stmt = pg_insert(TransportStop.__table__).values(rows)
    update_cols = {c.name: c for c in stmt.excluded if c.name not in ('id', 'atco_code', 'created_at')}
    stmt = stmt.on_conflict_do_update(index_elements=['atco_code'], set_=update_cols)
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def import_transport_stops(csv_file: str, dry_run: bool = False) -> dict:
    logger.info("Reading %s", csv_file)
    encoding = _detect_encoding(csv_file)
    logger.info("Detected encoding: %s", encoding)

    stats = {'rows_inserted': 0, 'rows_skipped': 0, 'errors': 0}
    db = SessionLocal()

    try:
        chunk_iter = pd.read_csv(
            csv_file, chunksize=CHUNK_SIZE, low_memory=False,
            encoding=encoding, on_bad_lines='skip',
        )

        for chunk_num, chunk in enumerate(chunk_iter, 1):
            try:
                cleaned = _clean_chunk(chunk)
                if cleaned.empty:
                    continue
                rows = cleaned.to_dict('records')
                for row in rows:
                    for k, v in row.items():
                        try:
                            if pd.isna(v):
                                row[k] = None
                        except (TypeError, ValueError):
                            pass

                if chunk_num % 25 == 0 or chunk_num == 1:
                    logger.info("Chunk %d: %d rows (%d total)", chunk_num, len(rows), stats['rows_inserted'])

                if dry_run:
                    stats['rows_inserted'] += len(rows)
                    continue

                inserted = _bulk_upsert(db, rows)
                stats['rows_inserted'] += inserted
                db.commit()

            except Exception as e:
                logger.warning("Chunk %d error: %s", chunk_num, e)
                stats['errors'] += 1
                db.rollback()

        logger.info("Import complete: %d upserted, %d errors", stats['rows_inserted'], stats['errors'])
        return stats
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Import NaPTAN transport stops CSV')
    parser.add_argument('--csv-file', required=True, help='Path to Stops.csv')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    import_transport_stops(args.csv_file, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
