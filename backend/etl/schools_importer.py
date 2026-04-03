"""
DfE GIAS Schools Importer

Imports school data from the DfE "Get Information About Schools" (GIAS)
bulk CSV export into the schools table.

Usage:
    python -m backend.etl.schools_importer --csv-file /tmp/edubasealldata20260403.csv
    python -m backend.etl.schools_importer --csv-file /tmp/edubasealldata20260403.csv --dry-run
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

CHUNK_SIZE = 5_000

# Map GIAS CSV column names -> model column names
COLUMN_MAP = {
    'URN':                              'urn',
    'LA (name)':                        'la_name',
    'EstablishmentName':                'establishment_name',
    'TypeOfEstablishment (name)':       'type_of_establishment',
    'PhaseOfEducation (name)':          'phase_of_education',
    'StatutoryLowAge':                  'statutory_low_age',
    'StatutoryHighAge':                 'statutory_high_age',
    'Boarders (code)':                  '_boarders_code',
    'NurseryProvision (name)':          'nursery_provision',
    'OfficialSixthForm (name)':         'has_sixth_form',
    'Gender (name)':                    'gender',
    'ReligiousCharacter (name)':        'religious_character',
    'AdmissionsPolicy (code)':          '_admissions_code',
    'SchoolCapacity':                   'school_capacity',
    'NumberOfPupils':                   'number_of_pupils',
    'NumberOfBoys':                     'number_of_boys',
    'NumberOfGirls':                    'number_of_girls',
    'Street':                           'street',
    'Locality':                         'locality',
    'Address3':                         'address3',
    'Town':                             'town',
    'County (name)':                    'county',
    'Postcode':                         'postcode',
    'SchoolWebsite':                    'school_website',
    'TelephoneNum':                     'telephone_num',
    'HeadTitle (name)':                 'head_title',
    'HeadFirstName':                    'head_first_name',
    'HeadLastName':                     'head_last_name',
    'Easting':                          'easting',
    'Northing':                         'northing',
}

KEEP_COLUMNS = [v for v in COLUMN_MAP.values() if not v.startswith('_')]


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Rename, select, derive booleans, and type-cast columns."""
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    # Derive is_boarding: Boarders (code) == 3 means boarding school
    if '_boarders_code' in chunk.columns:
        chunk['is_boarding'] = pd.to_numeric(chunk['_boarders_code'], errors='coerce') == 3
    else:
        chunk['is_boarding'] = False

    # Derive is_selective: AdmissionsPolicy (code) == 2 means selective
    if '_admissions_code' in chunk.columns:
        chunk['is_selective'] = pd.to_numeric(chunk['_admissions_code'], errors='coerce') == 2
    else:
        chunk['is_selective'] = False

    # Select final columns
    all_cols = KEEP_COLUMNS + ['is_boarding', 'is_selective']
    available = [c for c in all_cols if c in chunk.columns]
    chunk = chunk[available].copy()

    # URN is required
    chunk['urn'] = pd.to_numeric(chunk['urn'], errors='coerce')
    chunk = chunk.dropna(subset=['urn'])
    chunk['urn'] = chunk['urn'].astype(int)

    # Numeric columns — use nullable Int64 so NaN becomes <NA> not float nan
    for col in ('statutory_low_age', 'statutory_high_age', 'school_capacity',
                'number_of_pupils', 'number_of_boys', 'number_of_girls',
                'easting', 'northing'):
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce').astype('Int64')

    # Clean postcode
    if 'postcode' in chunk.columns:
        chunk['postcode'] = chunk['postcode'].astype(str).str.strip().str.upper()
        chunk.loc[chunk['postcode'].isin(['', 'NAN', 'NONE']), 'postcode'] = None

    # String length limits
    str_limits = {
        'la_name': 100, 'establishment_name': 200, 'type_of_establishment': 100,
        'phase_of_education': 50, 'nursery_provision': 50, 'has_sixth_form': 50,
        'gender': 20, 'religious_character': 100, 'street': 200,
        'locality': 200, 'address3': 200, 'town': 100, 'county': 100,
        'postcode': 10, 'school_website': 500, 'telephone_num': 30,
        'head_title': 20, 'head_first_name': 100, 'head_last_name': 100,
    }
    for col, limit in str_limits.items():
        if col in chunk.columns:
            chunk[col] = chunk[col].astype(str).str[:limit]
            chunk.loc[chunk[col].isin(['nan', 'None', '']), col] = None

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _bulk_upsert(db, rows: list) -> int:
    """Insert school rows, updating on URN conflict."""
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.school import School

    now = datetime.utcnow()
    for row in rows:
        row.setdefault('created_at', now)
        row.setdefault('updated_at', now)

    stmt = pg_insert(School.__table__).values(rows)
    # On conflict, update all fields (so re-imports refresh data)
    update_cols = {c.name: c for c in stmt.excluded if c.name not in ('id', 'urn', 'created_at')}
    stmt = stmt.on_conflict_do_update(
        index_elements=['urn'],
        set_=update_cols,
    )
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def import_schools(csv_file: str, dry_run: bool = False) -> dict:
    """Import GIAS schools CSV into the schools table."""
    logger.info("Reading %s", csv_file)

    stats = {'rows_inserted': 0, 'rows_skipped': 0, 'errors': 0}
    db = SessionLocal()

    try:
        chunk_iter = pd.read_csv(
            csv_file,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding='cp1252',
            on_bad_lines='skip',
        )

        for chunk_num, chunk in enumerate(chunk_iter, 1):
            try:
                cleaned = _clean_chunk(chunk)
                if cleaned.empty:
                    continue
                rows = cleaned.to_dict('records')
                # Convert pandas NA/NaT/nan to Python None for SQLAlchemy
                for row in rows:
                    for k, v in row.items():
                        if pd.isna(v):
                            row[k] = None
                logger.info("Chunk %d: %d rows cleaned", chunk_num, len(rows))

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
    parser = argparse.ArgumentParser(description='Import DfE GIAS schools CSV')
    parser.add_argument('--csv-file', required=True, help='Path to edubasealldata CSV file')
    parser.add_argument('--dry-run', action='store_true', help='Parse and count without inserting')
    args = parser.parse_args()

    import_schools(args.csv_file, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
