"""
Land Registry Price Paid Data Importer
Downloads and imports 10 years of UK property sales history from Land Registry
Used for valuation model training and area trend analysis
"""

import os
import sys
import csv
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import click
from tqdm import tqdm
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.models.sales_history import SalesHistory
from backend.models.base import Base

load_dotenv()


class LandRegistryImporter:
    """
    Imports Land Registry Price Paid Data (PPD)
    Open Government Licence v3.0: https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads
    """

    # Land Registry PPD CSV column mapping
    CSV_COLUMNS = [
        'transaction_id',  # Unique transaction identifier
        'price',           # Sale price
        'date_of_transfer',# Sale date
        'postcode',        # Property postcode
        'property_type',   # D/S/T/F (Detached/Semi/Terraced/Flat)
        'old_new',         # Y/N (New build/Established)
        'duration',        # F/L (Freehold/Leasehold)
        'paon',            # Primary Addressable Object Name
        'saon',            # Secondary Addressable Object Name
        'street',          # Street name
        'locality',        # Locality
        'town',            # Town/City
        'district',        # District
        'county',          # County
        'ppd_category',    # A/B (Standard price paid/Additional price paid)
        'record_status'    # A/C/D (Addition/Change/Delete)
    ]

    # Property type mapping
    PROPERTY_TYPE_MAP = {
        'D': 'detached',
        'S': 'semi-detached',
        'T': 'terraced',
        'F': 'flat',
        'O': 'other'
    }

    def __init__(self, db_session: Session):
        self.session = db_session
        self.base_url = os.getenv(
            'LAND_REGISTRY_DATA_URL',
            'http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com'
        )

    def download_price_paid_data(self, year: int, part: int = None) -> Optional[str]:
        """
        Download Land Registry Price Paid Data CSV for a specific year

        Args:
            year: Year to download (e.g., 2023)
            part: Part number for older multi-part years (1 or 2), None for single-part years

        Returns:
            Path to downloaded CSV file, or None if download failed
        """
        if part:
            # Older data split into two parts
            filename = f"pp-{year}-part{part}.csv"
        else:
            # Recent data in single file
            filename = f"pp-{year}.csv"

        url = f"{self.base_url}/{filename}"
        output_path = f"tmp/{filename}"

        # Create tmp directory if it doesn't exist
        os.makedirs('tmp', exist_ok=True)

        try:
            logger.info(f"Downloading {filename} from Land Registry...")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Get file size for progress bar
            file_size = int(response.headers.get('content-length', 0))

            with open(output_path, 'wb') as f, tqdm(
                desc=filename,
                total=file_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in response.iter_content(chunk_size=8192):
                    size = f.write(chunk)
                    bar.update(size)

            logger.info(f"Downloaded {filename} to {output_path}")
            return output_path

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {filename}: {e}")
            return None

    def parse_csv_row(self, row: List[str]) -> Optional[Dict]:
        """
        Parse a single CSV row into a dictionary

        Args:
            row: List of CSV values

        Returns:
            Dictionary of parsed data, or None if invalid
        """
        if len(row) != len(self.CSV_COLUMNS):
            logger.warning(f"Invalid row length: {len(row)} (expected {len(self.CSV_COLUMNS)})")
            return None

        try:
            # Parse data
            data = dict(zip(self.CSV_COLUMNS, row))

            # Build full address
            address_parts = [
                data['saon'],
                data['paon'],
                data['street'],
                data['locality'],
            ]
            full_address = ', '.join(filter(None, address_parts))

            # Parse date
            sale_date = datetime.strptime(data['date_of_transfer'], '%Y-%m-%d %H:%M').date()

            # Parse price
            sale_price = float(data['price'])

            # Normalize property type
            property_type = self.PROPERTY_TYPE_MAP.get(data['property_type'], 'other')

            return {
                'transaction_id': data['transaction_id'].strip('{}'),
                'sale_date': sale_date,
                'sale_price': sale_price,
                'address': full_address,
                'postcode': data['postcode'],
                'town': data['town'],
                'county': data['county'],
                'property_type': property_type,
                'old_new': data['old_new'],
                'duration': data['duration'],
                'ppd_category_type': data['ppd_category'],
                'record_status': data['record_status']
            }

        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse row: {e}")
            return None

    def import_csv(self, csv_path: str, batch_size: int = 5000) -> int:
        """
        Import Land Registry CSV data into database

        Args:
            csv_path: Path to CSV file
            batch_size: Number of records to insert per batch

        Returns:
            Number of records imported
        """
        logger.info(f"Importing {csv_path}...")

        records_imported = 0
        batch = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Count total lines for progress bar
                total_lines = sum(1 for line in f)
                f.seek(0)

                reader = csv.reader(f)

                with tqdm(total=total_lines, desc="Importing records") as pbar:
                    for row in reader:
                        parsed = self.parse_csv_row(row)

                        if parsed:
                            batch.append(SalesHistory(**parsed))

                        # Batch insert when batch_size reached
                        if len(batch) >= batch_size:
                            records_imported += self._upsert_batch(batch)
                            batch = []

                        pbar.update(1)

                # Insert remaining records
                if batch:
                    records_imported += self._upsert_batch(batch)

            logger.info(f"Imported {records_imported} records from {csv_path}")
            return records_imported

        except Exception as e:
            logger.error(f"Error importing {csv_path}: {e}")
            self.session.rollback()
            raise

    def _upsert_batch(self, batch: list) -> int:
        """Insert batch with ON CONFLICT DO NOTHING on transaction_id (idempotent re-runs)."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        if not batch:
            return 0
        rows = [
            {c.key: getattr(obj, c.key) for c in obj.__table__.columns}
            for obj in batch
        ]
        stmt = pg_insert(SalesHistory.__table__).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=['transaction_id'])
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount if result.rowcount >= 0 else len(rows)

    def import_year_range(self, start_year: int, end_year: int, batch_size: int = 5000) -> int:
        """
        Import Land Registry data for a range of years

        Args:
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)
            batch_size: Batch size for database inserts

        Returns:
            Total number of records imported
        """
        total_imported = 0

        for year in range(start_year, end_year + 1):
            # Try downloading single-part file first
            csv_path = self.download_price_paid_data(year)

            if csv_path and os.path.exists(csv_path):
                total_imported += self.import_csv(csv_path, batch_size)
                # Clean up downloaded file
                os.remove(csv_path)
            else:
                # Try multi-part files for older years
                for part in [1, 2]:
                    csv_path = self.download_price_paid_data(year, part)

                    if csv_path and os.path.exists(csv_path):
                        total_imported += self.import_csv(csv_path, batch_size)
                        os.remove(csv_path)

        return total_imported


@click.command()
@click.option('--years', default=10, help='Number of years to import (default: 10)')
@click.option('--start-year', type=int, help='Starting year (overrides --years)')
@click.option('--end-year', type=int, help='Ending year (overrides --years)')
@click.option('--batch-size', default=5000, help='Batch size for database inserts')
@click.option('--test', is_flag=True, help='Test mode: import only 1 year')
def main(years: int, start_year: Optional[int], end_year: Optional[int], batch_size: int, test: bool):
    """
    Land Registry Price Paid Data Importer

    Downloads and imports historical property sales data from Land Registry.
    Data is used for ML valuation model training and area trend analysis.

    Examples:
        # Import last 10 years of data
        python land_registry_importer.py --years 10

        # Import specific year range
        python land_registry_importer.py --start-year 2015 --end-year 2025

        # Test with 1 year
        python land_registry_importer.py --test

    Attribution:
        Contains Land Registry data © Crown copyright and database right 2026
        Licensed under Open Government Licence v3.0
    """
    # Configure logging
    logger.add("logs/land_registry_import.log", rotation="100 MB")

    # Determine year range
    current_year = datetime.now().year

    if test:
        start_year = current_year - 1
        end_year = current_year - 1
    elif start_year and end_year:
        pass  # Use provided years
    else:
        # Calculate from --years parameter
        end_year = current_year - 1  # Previous year (current year data may be incomplete)
        start_year = end_year - years + 1

    logger.info(f"Importing Land Registry data from {start_year} to {end_year}")

    # Create database connection — prefer DATABASE_URL if set, otherwise build from components
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        DATABASE_URL = (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()

    try:
        # Create importer instance
        importer = LandRegistryImporter(db_session)

        # Import data
        total_records = importer.import_year_range(start_year, end_year, batch_size)

        logger.info(f"Import complete! Total records imported: {total_records}")
        print(f"\n✅ Successfully imported {total_records} Land Registry sales records")
        print(f"📅 Year range: {start_year} - {end_year}")

    except Exception as e:
        logger.error(f"Import failed: {e}")
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)

    finally:
        db_session.close()


if __name__ == '__main__':
    main()
