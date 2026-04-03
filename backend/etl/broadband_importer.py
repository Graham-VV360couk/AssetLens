"""
Ofcom Broadband Coverage Importer

Imports Ofcom fixed broadband coverage data per postcode from the
residential postcode-level CSVs (inside the zip file).

Usage:
    python -m backend.etl.broadband_importer --zip-file tmp/202507_fixed_coverage_r01/202507_fixed_pc_coverage_r01.zip
    python -m backend.etl.broadband_importer --zip-file tmp/202507_fixed_coverage_r01/202507_fixed_pc_coverage_r01.zip --dry-run
"""
import argparse
import logging
import os
import sys
import zipfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd

from backend.models.base import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHUNK_SIZE = 2_000

COLUMN_MAP = {
    'postcode_space':                                   'postcode',
    'SFBB availability (% premises)':                   'sfbb_availability',
    'UFBB (100Mbit/s) availability (% premises)':       'ufbb_100_availability',
    'UFBB availability (% premises)':                   'ufbb_availability',
    'Gigabit availability (% premises)':                'gigabit_availability',
    '% of premises with 0<2Mbit/s download speed':      'pct_below_2',
    '% of premises with 2<5Mbit/s download speed':      'pct_2_to_5',
    '% of premises with 5<10Mbit/s download speed':     'pct_5_to_10',
    '% of premises with 10<30Mbit/s download speed':    'pct_10_to_30',
    '% of premises with 30<300Mbit/s download speed':   'pct_30_to_300',
    '% of premises with >=300Mbit/s download speed':    'pct_above_300',
    '% of premises unable to receive 2Mbit/s':          'pct_unable_2',
    '% of premises unable to receive 5Mbit/s':          'pct_unable_5',
    '% of premises unable to receive 10Mbit/s':         'pct_unable_10',
    '% of premises unable to receive 30Mbit/s':         'pct_unable_30',
    '% of premises below the USO':                      'pct_below_uso',
    '% of premises with NGA':                           'pct_nga',
    '% of premises able to receive decent broadband from FWA': 'pct_fwa_decent',
}

KEEP_COLUMNS = list(COLUMN_MAP.values())


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    # Drop the raw 'postcode' column (no space) to avoid clash with postcode_space rename
    if 'postcode' in chunk.columns and 'postcode_space' in chunk.columns:
        chunk = chunk.drop(columns=['postcode'])

    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in chunk.columns}
    chunk = chunk.rename(columns=rename_map)

    available = [c for c in KEEP_COLUMNS if c in chunk.columns]
    chunk = chunk[available].copy()

    if 'postcode' not in chunk.columns:
        return pd.DataFrame()
    chunk['postcode'] = chunk['postcode'].astype(str).str.strip()
    chunk = chunk[chunk['postcode'].str.len() > 0]
    chunk = chunk[chunk['postcode'] != 'nan']

    # All percentage columns are float
    float_cols = [c for c in KEEP_COLUMNS if c != 'postcode']
    for col in float_cols:
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

    chunk = chunk.where(chunk.notna(), other=None)
    return chunk


def _bulk_upsert(db, rows: list) -> int:
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.broadband import BroadbandCoverage

    now = datetime.utcnow()
    for row in rows:
        row.setdefault('created_at', now)
        row.setdefault('updated_at', now)

    stmt = pg_insert(BroadbandCoverage.__table__).values(rows)
    update_cols = {c.name: c for c in stmt.excluded if c.name not in ('id', 'postcode', 'created_at')}
    stmt = stmt.on_conflict_do_update(index_elements=['postcode'], set_=update_cols)
    result = db.execute(stmt)
    return result.rowcount if result.rowcount >= 0 else len(rows)


def import_broadband(zip_file: str, dry_run: bool = False) -> dict:
    """Import Ofcom broadband residential postcode CSVs from zip."""
    logger.info("Reading %s", zip_file)

    stats = {'files_processed': 0, 'rows_inserted': 0, 'errors': 0}
    db = SessionLocal()

    try:
        with zipfile.ZipFile(zip_file) as zf:
            csv_files = sorted([f for f in zf.namelist()
                                if 'postcode_res_files' in f and f.endswith('.csv')])
            logger.info("Found %d residential postcode CSVs in zip", len(csv_files))

            for file_idx, csv_name in enumerate(csv_files, 1):
                logger.info("[%d/%d] %s", file_idx, len(csv_files), csv_name)
                try:
                    with zf.open(csv_name) as f:
                        chunk_iter = pd.read_csv(
                            f, chunksize=CHUNK_SIZE, low_memory=False,
                            encoding='utf-8', on_bad_lines='skip',
                        )

                        file_rows = 0
                        for chunk in chunk_iter:
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

                                if dry_run:
                                    file_rows += len(rows)
                                    continue

                                inserted = _bulk_upsert(db, rows)
                                file_rows += inserted

                            except Exception as ce:
                                logger.warning("Chunk error in %s: %s", csv_name, ce)
                                stats['errors'] += 1
                                db.rollback()

                    db.commit()
                    stats['files_processed'] += 1
                    stats['rows_inserted'] += file_rows
                    logger.info("  -> %d rows (%d total)", file_rows, stats['rows_inserted'])

                except Exception as e:
                    logger.error("Error processing %s: %s", csv_name, e)
                    stats['errors'] += 1
                    db.rollback()

        logger.info(
            "Import complete: %d files, %d rows, %d errors",
            stats['files_processed'], stats['rows_inserted'], stats['errors'],
        )
        return stats
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Import Ofcom broadband coverage data')
    parser.add_argument('--zip-file', required=True, help='Path to Ofcom postcode coverage zip')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    import_broadband(args.zip_file, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
