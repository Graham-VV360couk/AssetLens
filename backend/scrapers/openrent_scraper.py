"""
OpenRent whole-property rental scraper.
OpenRent is a landlord-direct letting platform. Listings include full postcodes,
bedrooms, and monthly rent — ideal for yield calculations.

Check robots.txt / ToS before running in production. OpenRent does not explicitly
prohibit scraping for non-commercial research in the way Rightmove does, but use
responsibly: rate-limit requests and identify your client.

Run:
    python -m backend.scrapers.openrent_scraper NG1 NG2 NG7 --pages 3
    python -m backend.scrapers.openrent_scraper --districts-from-db --pages 5
"""
import logging
import os
import re
import sys
import time
from datetime import datetime, date
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy import func
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.rental import Rental
from backend.models.property import Property

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'AssetLens/1.0 (property investment research tool; '
        'contact@assetlens.co.uk)'
    ),
    'Accept-Language': 'en-GB,en;q=0.9',
}
RATE_LIMIT = 3.0  # seconds between requests — be polite


def _get(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        time.sleep(RATE_LIMIT)
        r = session.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        logger.warning('GET %s failed: %s', url, e)
        return None


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    # Strip currency/commas, find number
    cleaned = re.sub(r'[£,\s]', '', text)
    m = re.search(r'\d+', cleaned)
    if not m:
        return None
    price = float(m.group(0))
    # Convert weekly (pcw) to monthly
    if re.search(r'p[. ]?c[. ]?w|per week|/week', text, re.IGNORECASE):
        price = price * 52 / 12
    return price


def _extract_postcode(text: str) -> str:
    """Extract UK postcode from a string, or return empty string."""
    m = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', text, re.IGNORECASE)
    return m.group(1).upper().strip() if m else ''


class OpenRentScraper:
    """
    Scrapes OpenRent.co.uk for whole-property to-rent listings.
    Search URL pattern: /properties-to-rent/?term=POSTCODE_DISTRICT&bedrooms=N&max_bedrooms=N
    """
    BASE = 'https://www.openrent.co.uk'
    SEARCH = BASE + '/properties-to-rent/'

    def __init__(self):
        self.session = requests.Session()

    def scrape_district(self, district: str, max_pages: int = 5) -> list[dict]:
        """Scrape all listings in a postcode district (e.g. 'NG1')."""
        results = []
        for page in range(1, max_pages + 1):
            params = f'?term={district}&page={page}'
            soup = _get(self.SEARCH + params, self.session)
            if not soup:
                break

            listings = soup.select(
                'li.listing, div.listing, article[data-listing-id], '
                '.property-listing, [data-property-id]'
            )

            # Fallback: OpenRent renders listings as <a> cards
            if not listings:
                listings = soup.select('a[href*="/property/"]')

            if not listings:
                logger.info('OpenRent %s page %d: no listings found, stopping', district, page)
                break

            for el in listings:
                try:
                    item = self._parse_listing(el, district)
                    if item:
                        results.append(item)
                except Exception as e:
                    logger.debug('Parse error: %s', e)

            logger.info('OpenRent %s page %d: %d total results so far', district, page, len(results))

        return results

    def _parse_listing(self, el, fallback_district: str) -> Optional[dict]:
        text = el.get_text(' ', strip=True)

        # Rent
        rent_el = el.select_one(
            '.price, .rent, [class*="price"], [class*="rent"], '
            '[data-price], strong'
        )
        rent_text = rent_el.get_text(strip=True) if rent_el else ''
        # Also search in full text for £NNN pattern
        if not rent_text:
            m = re.search(r'£[\d,]+', text)
            rent_text = m.group(0) if m else ''
        rent = _parse_price(rent_text)
        if not rent or rent < 200:  # sanity check
            return None

        # Bedrooms
        beds_el = el.select_one('[class*="bed"], [data-beds]')
        beds_text = beds_el.get_text(strip=True) if beds_el else ''
        if not beds_text:
            beds_text = text
        beds_m = re.search(r'(\d)\s*(?:bed|bedroom|bd)', beds_text, re.IGNORECASE)
        bedrooms = int(beds_m.group(1)) if beds_m else None

        # Property type
        type_m = re.search(
            r'\b(flat|apartment|studio|terraced|semi.detached|detached|bungalow|maisonette)\b',
            text, re.IGNORECASE
        )
        property_type = type_m.group(1).lower() if type_m else None
        if property_type in ('apartment',):
            property_type = 'flat'
        if property_type and 'semi' in property_type:
            property_type = 'semi-detached'

        # Postcode
        postcode = _extract_postcode(text)
        if not postcode:
            # Use district as approximate postcode
            postcode = fallback_district

        # Source URL
        link = el.select_one('a[href]') or (el if el.name == 'a' else None)
        source_url = self.BASE + link['href'] if link and link.get('href', '').startswith('/') else ''

        return {
            'postcode': postcode,
            'rent_monthly': rent,
            'bedrooms': bedrooms,
            'property_type': property_type,
            'source': 'openrent',
            'source_url': source_url,
            'is_hmo': False,
            'date_listed': date.today(),
        }


class OpenRentImporter:
    """Saves OpenRent listings and creates per-district-bedrooms aggregates."""

    def __init__(self, db: Session):
        self.db = db
        self.stats = {'new': 0, 'aggregated': 0, 'skipped': 0, 'errors': 0}

    def import_listings(self, listings: list[dict]):
        for listing in listings:
            try:
                self._save_listing(listing)
            except Exception as e:
                logger.warning('Error saving rental: %s', e)
                self.stats['errors'] += 1

        # Build per-district+bedrooms aggregates
        districts = set()
        for l in listings:
            pc = l.get('postcode', '')
            districts.add(pc.split(' ')[0] if ' ' in pc else pc[:4])

        for district in districts:
            try:
                self._aggregate_district(district)
            except Exception as e:
                logger.warning('Aggregation error for %s: %s', district, e)

        self.db.commit()

    def _save_listing(self, listing: dict):
        rental = Rental(
            rent_monthly=listing['rent_monthly'],
            postcode=listing['postcode'],
            bedrooms=listing.get('bedrooms'),
            property_type=listing.get('property_type'),
            date_listed=listing['date_listed'],
            source=listing['source'],
            source_url=listing.get('source_url', ''),
            is_hmo=False,
            is_aggregated=False,
        )
        self.db.add(rental)
        self.stats['new'] += 1

    def _aggregate_district(self, district: str):
        """
        Create/update median rent aggregates per district+bedrooms.
        These are what the scoring service queries for yield calculations.
        """
        # Fetch all non-aggregated whole-property listings in this district
        rows = (
            self.db.query(Rental)
            .filter(
                Rental.postcode.like(f'{district}%'),
                Rental.is_aggregated == False,
                Rental.is_hmo == False,
                Rental.rent_monthly != None,
                Rental.rent_monthly > 200,
            )
            .all()
        )
        if not rows:
            return

        # Group by bedrooms
        by_beds: dict[Optional[int], list[float]] = {}
        for r in rows:
            by_beds.setdefault(r.bedrooms, []).append(r.rent_monthly)

        for beds, rents in by_beds.items():
            if not rents:
                continue
            median_rent = sorted(rents)[len(rents) // 2]

            # Upsert
            agg = (
                self.db.query(Rental)
                .filter(
                    Rental.postcode == district,
                    Rental.is_aggregated == True,
                    Rental.bedrooms == beds,
                    Rental.is_hmo == False,
                )
                .first()
            )
            if agg:
                agg.rent_monthly = median_rent
                agg.date_listed = date.today()
            else:
                self.db.add(Rental(
                    postcode=district,
                    rent_monthly=median_rent,
                    bedrooms=beds,
                    is_aggregated=True,
                    is_hmo=False,
                    date_listed=date.today(),
                    source='openrent_aggregate',
                ))
            self.stats['aggregated'] += 1

        logger.info(
            'OpenRent aggregates for %s: %s',
            district,
            {str(b) + 'bd': round(sorted(r)[len(r)//2]) for b, r in by_beds.items()}
        )


def get_active_districts(db: Session) -> list[str]:
    """Return unique postcode districts from active property listings."""
    rows = (
        db.query(Property.postcode)
        .filter(Property.status == 'active', Property.postcode != None, Property.postcode != '')
        .distinct()
        .all()
    )
    seen = set()
    districts = []
    for (pc,) in rows:
        d = pc.split(' ')[0].upper() if ' ' in pc else pc.upper()[:4]
        if d and d not in seen:
            seen.add(d)
            districts.append(d)
    return districts


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scrape OpenRent for whole-property rental data')
    parser.add_argument(
        'districts', nargs='*',
        help='Postcode districts to scrape (e.g. NG1 NG2 LS1). '
             'Omit to use --districts-from-db.'
    )
    parser.add_argument(
        '--districts-from-db', action='store_true',
        help='Automatically scrape all postcode districts that have active properties in DB'
    )
    parser.add_argument('--pages', type=int, default=5, help='Max pages per district (default 5)')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        scraper = OpenRentScraper()
        importer = OpenRentImporter(db)

        districts = list(args.districts)
        if args.districts_from_db or not districts:
            db_districts = get_active_districts(db)
            logger.info('Found %d districts in DB: %s', len(db_districts), db_districts[:20])
            districts = districts + [d for d in db_districts if d not in districts]

        if not districts:
            logger.error('No districts specified and none found in DB.')
            return

        logger.info('Scraping %d districts: %s', len(districts), districts)
        all_listings = []
        for district in districts:
            logger.info('Scraping district %s...', district)
            listings = scraper.scrape_district(district, max_pages=args.pages)
            logger.info('%s: %d listings found', district, len(listings))
            all_listings.extend(listings)

        logger.info('Total listings scraped: %d', len(all_listings))
        importer.import_listings(all_listings)
        logger.info('Import complete: %s', importer.stats)
    finally:
        db.close()


if __name__ == '__main__':
    main()
