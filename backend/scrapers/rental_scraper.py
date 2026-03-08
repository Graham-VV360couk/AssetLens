"""
Rental Data Scraper (Task #11)
Scrapes SpareRoom for room rental data and aggregates by postcode.
Scheduled weekly.
"""
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from sqlalchemy import func
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.rental import Rental

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'AssetLens/1.0 (property investment research tool; contact@assetlens.co.uk)',
}
RATE_LIMIT = 3.0  # seconds between requests


def _get(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        time.sleep(RATE_LIMIT)
        r = session.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        logger.warning("GET %s failed: %s", url, e)
        return None


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r'[\d,]+', text.replace(',', ''))
    return float(m.group(0)) if m else None


class SpareRoomScraper:
    """
    Scrapes SpareRoom.co.uk for HMO room rental prices.
    Returns room listings with postcode for aggregate yield calculations.
    """
    BASE = 'https://www.spareroom.co.uk'
    SEARCH = BASE + '/flatshare/'

    def __init__(self):
        self.session = requests.Session()

    def search_area(self, location: str, max_pages: int = 5) -> list:
        results = []
        for page in range(1, max_pages + 1):
            params = {'location': location, 'page': page, 'per_page': 50}
            url = self.SEARCH + '?' + urlencode(params)
            soup = _get(url, self.session)
            if not soup:
                break

            listings = soup.select('.listing-result, article.listing, [data-listing-id]')
            if not listings:
                break

            for listing in listings:
                try:
                    item = self._parse_listing(listing)
                    if item:
                        results.append(item)
                except Exception as e:
                    logger.debug("Parse error: %s", e)

            logger.info("SpareRoom %s page %d: %d results", location, page, len(results))

        return results

    def _parse_listing(self, el) -> Optional[dict]:
        price_el = el.select_one('.price, .cost, [data-price]')
        addr_el = el.select_one('.address, .location, h2, h3')
        rooms_el = el.select_one('.rooms, [data-rooms]')
        link = el.select_one('a[href]')

        if not price_el or not addr_el:
            return None

        price_text = price_el.get_text(strip=True)
        # Convert weekly to monthly
        price = _parse_price(price_text)
        if price and 'pw' in price_text.lower():
            price = price * 52 / 12

        addr = addr_el.get_text(strip=True)
        postcode_match = re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', addr, re.IGNORECASE)
        postcode = postcode_match.group(0).upper() if postcode_match else ''

        rooms = None
        if rooms_el:
            rm = re.search(r'\d+', rooms_el.get_text())
            rooms = int(rm.group(0)) if rm else None

        return {
            'address': addr,
            'postcode': postcode,
            'rent_per_room': price,
            'num_rooms': rooms or 1,
            'source': 'spareroom',
            'source_url': self.BASE + link['href'] if link else '',
            'is_hmo': True,
            'date_listed': datetime.utcnow(),
        }


class RentalImporter:
    """Saves rental listings and creates postcode aggregates"""

    def __init__(self, db: Session):
        self.db = db
        self.stats = {'new': 0, 'aggregated': 0, 'errors': 0}

    def import_listings(self, listings: list):
        for listing in listings:
            try:
                self._save_listing(listing)
            except Exception as e:
                logger.warning("Error saving rental: %s", e)
                self.stats['errors'] += 1

        # Aggregate by postcode district
        postcodes = set(l.get('postcode', '') for l in listings if l.get('postcode'))
        for postcode in postcodes:
            try:
                self._aggregate_postcode(postcode)
            except Exception as e:
                logger.warning("Aggregation error for %s: %s", postcode, e)

        self.db.commit()

    def _save_listing(self, listing: dict):
        rental = Rental(
            rent_per_room=listing.get('rent_per_room'),
            rent_monthly=listing.get('rent_monthly') or (
                listing['rent_per_room'] * listing.get('num_rooms', 1)
                if listing.get('rent_per_room') else None
            ),
            postcode=listing.get('postcode', ''),
            address=listing.get('address', ''),
            num_rooms=listing.get('num_rooms', 1),
            date_listed=listing.get('date_listed', datetime.utcnow()),
            source=listing.get('source', 'spareroom'),
            source_url=listing.get('source_url', ''),
            is_hmo=listing.get('is_hmo', False),
            is_aggregated=False,
        )
        self.db.add(rental)
        self.stats['new'] += 1

    def _aggregate_postcode(self, postcode: str):
        """Calculate average room rent for postcode district (first part of postcode)"""
        district = postcode.split(' ')[0] if ' ' in postcode else postcode[:4]
        rows = (
            self.db.query(Rental)
            .filter(
                Rental.postcode.like(f"{district}%"),
                Rental.is_aggregated == False,
                Rental.rent_per_room != None,
            )
            .all()
        )
        if not rows:
            return

        avg_room = sum(r.rent_per_room for r in rows) / len(rows)
        avg_total = avg_room * 4  # assume 4-bed HMO default

        # Upsert aggregate record
        agg = (
            self.db.query(Rental)
            .filter(Rental.postcode == district, Rental.is_aggregated == True)
            .first()
        )
        if agg:
            agg.rent_per_room = avg_room
            agg.rent_monthly = avg_total
            agg.date_listed = datetime.utcnow()
        else:
            self.db.add(Rental(
                postcode=district,
                rent_per_room=avg_room,
                rent_monthly=avg_total,
                is_aggregated=True,
                is_hmo=True,
                date_listed=datetime.utcnow(),
                source='aggregate',
            ))
        self.stats['aggregated'] += 1


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scrape rental data')
    parser.add_argument('locations', nargs='*', default=['London', 'Manchester', 'Birmingham',
                        'Leeds', 'Sheffield', 'Liverpool', 'Bristol', 'Leicester'],
                        help='Locations to scrape')
    parser.add_argument('--pages', type=int, default=5, help='Pages per location')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        scraper = SpareRoomScraper()
        importer = RentalImporter(db)

        all_listings = []
        for loc in args.locations:
            logger.info("Scraping %s...", loc)
            listings = scraper.search_area(loc, max_pages=args.pages)
            all_listings.extend(listings)

        logger.info("Total listings: %d", len(all_listings))
        importer.import_listings(all_listings)
        logger.info("Import complete: %s", importer.stats)
    finally:
        db.close()


if __name__ == '__main__':
    main()
