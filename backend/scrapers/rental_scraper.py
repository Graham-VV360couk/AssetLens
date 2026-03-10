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
import random
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
        seen_urls: set = set()
        for page in range(1, max_pages + 1):
            params = {'location': location, 'page': page, 'per_page': 50}
            url = self.SEARCH + '?' + urlencode(params)
            soup = _get(url, self.session)
            if not soup:
                break

            listings = soup.select('article.listing-card, .listing-result, article.listing, [data-listing-id]')
            if not listings:
                break

            new_count = 0
            for listing in listings:
                try:
                    item = self._parse_listing(listing)
                    if item:
                        url_key = item.get('source_url', '')
                        if url_key and url_key in seen_urls:
                            continue  # duplicate — already seen on a prior page
                        if url_key:
                            seen_urls.add(url_key)
                        results.append(item)
                        new_count += 1
                except Exception as e:
                    logger.debug("Parse error: %s", e)

            logger.info("SpareRoom %s page %d: %d new, %d total", location, page, new_count, len(results))
            if new_count == 0:
                logger.info("SpareRoom %s: no new results on page %d — stopping early", location, page)
                break

        return results

    def _parse_listing(self, el) -> Optional[dict]:
        link = el.select_one('a[href]')
        text = el.get_text(' ', strip=True)

        # Price — "£850 pcm" or "£195 pw"
        price_m = re.search(r'£([\d,]+)', text)
        if not price_m:
            return None
        price = _parse_price(price_m.group(0))
        if price and re.search(r'\bpw\b|per week', text, re.IGNORECASE):
            price = price * 52 / 12
        if not price or price < 100:
            return None

        # Postcode — SpareRoom shows district in parentheses e.g. "(NG1)" or "(NG1 2AB)"
        postcode_m = re.search(r'\(([A-Z]{1,2}\d{1,2}[A-Z]?(?:\s*\d[A-Z]{2})?)\)', text, re.IGNORECASE)
        if not postcode_m:
            postcode_m = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', text, re.IGNORECASE)
        postcode = postcode_m.group(1).upper().strip() if postcode_m else ''

        # Room type — studio = 0 bedrooms, otherwise 1 room per listing
        is_studio = bool(re.search(r'\bstudio\b', text, re.IGNORECASE))

        return {
            'address': text[:120],
            'postcode': postcode,
            'rent_per_room': price,
            'num_rooms': 1,
            'source': 'spareroom',
            'source_url': self.BASE + link['href'] if link else '',
            'is_hmo': not is_studio,
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
                try:
                    self.db.rollback()
                except Exception:
                    pass
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
    from backend.models.property import Property
    parser = argparse.ArgumentParser(description='Scrape SpareRoom HMO room rental data')
    parser.add_argument('locations', nargs='*', help='Postcode districts or city names to scrape')
    parser.add_argument('--districts-from-db', action='store_true',
                        help='Scrape all postcode districts with active properties')
    parser.add_argument('--pages', type=int, default=3, help='Pages per location')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        scraper = SpareRoomScraper()
        importer = RentalImporter(db)

        locations = list(args.locations)
        if args.districts_from_db or not locations:
            rows = (db.query(Property.postcode)
                    .filter(Property.status == 'active', Property.postcode != None, Property.postcode != '')
                    .distinct().all())
            seen, districts = set(), []
            for (pc,) in rows:
                d = pc.split(' ')[0].upper() if ' ' in pc else pc.upper()[:4]
                if d and d not in seen:
                    seen.add(d)
                    districts.append(d)
            logger.info('Found %d districts in DB', len(districts))
            locations = locations + [d for d in districts if d not in locations]

        if not locations:
            logger.error('No locations specified.')
            return

        all_listings = []
        for loc in locations:
            logger.info("Scraping %s...", loc)
            listings = scraper.search_area(loc, max_pages=args.pages)
            logger.info("%s: %d listings", loc, len(listings))
            all_listings.extend(listings)
            time.sleep(RATE_LIMIT)

        logger.info("Total listings: %d", len(all_listings))
        importer.import_listings(all_listings)
        logger.info("Import complete: %s", importer.stats)
    finally:
        db.close()


if __name__ == '__main__':
    main()
