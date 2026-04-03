"""
Planning Data Importer

Imports planning designation data from planning.data.gov.uk CSV exports.
Handles all dataset types (conservation areas, listed buildings, flood risk, etc.)
using a unified schema with dataset-specific field mapping.

Usage:
    python -m backend.etl.planning_importer --data-dir tmp/PlanningData
    python -m backend.etl.planning_importer --data-dir tmp/PlanningData --dry-run
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

CHUNK_SIZE = 2_000

# Common columns across all datasets
COMMON_MAP = {
    'dataset':              'dataset',
    'entity':               'entity',
    'name':                 'name',
    'reference':            'reference',
    'organisation':         'organisation',
    'start-date':           'start_date',
    'end-date':             'end_date',
    'entry-date':           'entry_date',
    'point':                '_point',       # parsed into lat/lng
    'notes':                'notes',
}

# Dataset-specific column mappings
EXTRA_MAP = {
    'listed-building-grade':        'listed_building_grade',
    'flood-risk-level':             'flood_risk_level',
    'flood-risk-type':              'flood_risk_type',
    'permitted-development-rights': 'permitted_dev_rights',
    'description':                  'description',
    'hectares':                     'hectares',
    'maximum-net-dwellings':        'max_net_dwellings',
    'minimum-net-dwellings':        'min_net_dwellings',
    'designation-date':             'designation_date',
    'ancient-woodland-status':      'ancient_woodland_status',
    'heritage-at-risk':             'heritage_at_risk',
}

ALL_MAP = {**COMMON_MAP, **EXTRA_MAP}

KEEP_COLUMNS = [v for v in ALL_MAP.values() if not v.startswith('_')]

# Regex to extract coordinates from POINT(lng lat) WKT
POINT_RE = re.compile(r'POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)')


def _parse_point(point_str):
    """Extract (latitude, longitude) from POINT(lng lat) WKT string."""
    if not point_str or not isinstance(point_str, str):
        return None, None
    m = POINT_RE.match(point_str.strip())
    if m:
        return float(m.group(2)), float(m.group(1))  # lat, lng
    return None, None


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Rename, select, parse points, and type-cast planning columns."""
    rename_map = {k: v for k, v in ALL_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    # Parse POINT WKT into lat/lng
    if '_point' in chunk.columns:
        coords = chunk['_point'].apply(lambda p: pd.Series(_parse_point(p), index=['latitude', 'longitude']))
        chunk['latitude'] = coords['latitude']
        chunk['longitude'] = coords['longitude']

    # Select columns we want
    available = [c for c in KEEP_COLUMNS + ['latitude', 'longitude'] if c in chunk.columns]
    # Deduplicate column list
    available = list(dict.fromkeys(available))
    chunk = chunk[available].copy()

    # Entity is required
    if 'entity' not in chunk.columns:
        return pd.DataFrame()
    chunk['entity'] = pd.to_numeric(chunk['entity'], errors='coerce')
    chunk = chunk.dropna(subset=['entity'])
    chunk['entity'] = chunk['entity'].astype(int)

    # Dataset is required
    if 'dataset' not in chunk.columns or chunk['dataset'].isna().all():
        return pd.DataFrame()

    # Date columns
    for col in ('start_date', 'end_date', 'entry_date', 'designation_date'):
        if col in chunk.columns:
            chunk[col] = pd.to_datetime(chunk[col], errors='coerce').dt.date

    # Numeric columns
    if 'hectares' in chunk.columns:
        chunk['hectares'] = pd.to_numeric(chunk['hectares'], errors='coerce')
    for col in ('max_net_dwellings', 'min_net_dwellings'):
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce').astype('Int64')

    # String length limits
    str_limits = {
        'dataset': 60, 'name': 500, 'reference': 200, 'organisation': 200,
        'listed_building_grade': 5, 'flood_risk_level': 10, 'flood_risk_type': 50,
        'ancient_woodland_status': 100, 'heritage_at_risk': 200,
    }
    for col, limit in str_limits.items():
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str[:limit]
            chunk.loc[chunk[col].isin(['nan', 'None', '']), col] = None

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _detect_encoding(csv_path: str) -> str:
    """Try common encodings and return the first that works."""
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'latin-1'


def _bulk_upsert(db, rows: list) -> int:
    """Insert planning rows, updating on (dataset, entity) conflict."""
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.planning_designation import PlanningDesignation

    now = datetime.utcnow()
    for row in rows:
        row.setdefault('created_at', now)
        row.setdefault('updated_at', now)

    stmt = pg_insert(PlanningDesignation.__table__).values(rows)
    update_cols = {c.name: c for c in stmt.excluded
                   if c.name not in ('id', 'dataset', 'entity', 'created_at')}
    stmt = stmt.on_conflict_do_update(
        index_elements=['dataset', 'entity'],
        set_=update_cols,
    )
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def import_planning_data(data_dir: str, dry_run: bool = False) -> dict:
    """Import all planning CSV files found in data_dir."""
    csv_files = sorted(glob.glob(f"{data_dir}/*.csv"))

    if not csv_files:
        logger.error("No CSV files found in %s", data_dir)
        return {'files_processed': 0, 'rows_inserted': 0, 'errors': 0}

    logger.info("Found %d CSV file(s) in %s", len(csv_files), data_dir)

    stats = {'files_processed': 0, 'rows_inserted': 0, 'errors': 0}
    db = SessionLocal()

    try:
        for file_idx, csv_path in enumerate(csv_files, 1):
            encoding = _detect_encoding(csv_path)
            basename = os.path.basename(csv_path)
            logger.info("[%d/%d] %s (encoding: %s)", file_idx, len(csv_files), basename, encoding)

            try:
                chunk_iter = pd.read_csv(
                    csv_path,
                    chunksize=CHUNK_SIZE,
                    low_memory=False,
                    encoding=encoding,
                    on_bad_lines='skip',
                )

                file_rows = 0
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

                        if dry_run:
                            file_rows += len(rows)
                            continue

                        inserted = _bulk_upsert(db, rows)
                        file_rows += inserted

                    except Exception as ce:
                        logger.warning("Chunk %d error in %s: %s", chunk_num, basename, ce)
                        stats['errors'] += 1
                        db.rollback()

                db.commit()
                stats['files_processed'] += 1
                stats['rows_inserted'] += file_rows
                logger.info("  -> %d rows from %s (%d total)", file_rows, basename, stats['rows_inserted'])

            except Exception as e:
                logger.error("Error processing %s: %s", basename, e)
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
    parser = argparse.ArgumentParser(description='Import planning.data.gov.uk CSV files')
    parser.add_argument('--data-dir', required=True, help='Directory containing planning CSVs')
    parser.add_argument('--dry-run', action='store_true', help='Parse and count without inserting')
    args = parser.parse_args()

    import_planning_data(args.data_dir, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
