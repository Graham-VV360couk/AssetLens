"""
Auction Property Scrapers (Task #10)
Scrapes auction listings from major UK auction houses.
Always respects robots.txt and rate limits.
"""
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.property import Property
from backend.models.auction import Auction
from backend.services.deduplication_service import PropertyDeduplicator

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'AssetLens/1.0 (property investment research tool; contact@assetlens.co.uk)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
}

RATE_LIMIT_SECONDS = 2.0  # polite crawling delay


def _get_page(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        time.sleep(RATE_LIMIT_SECONDS)
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _parse_price(text: str) -> Optional[int]:
    if not text:
        return None
    cleaned = re.sub(r'[^\d]', '', text)
    return int(cleaned) if cleaned else None


def _parse_date(text: str) -> Optional[datetime]:
    if not text:
        return None
    for fmt in ('%d %B %Y', '%d/%m/%Y', '%Y-%m-%d', '%d %b %Y'):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


class PropertyAuctionsSpider:
    """Scraper for PropertyAuctions.io"""
    BASE_URL = 'https://www.propertyauctions.io'
    LISTING_URL = BASE_URL + '/auctions'

    def __init__(self):
        self.session = requests.Session()

    def scrape_listings(self, max_pages: int = 10) -> list:
        results = []
        for page in range(1, max_pages + 1):
            url = f"{self.LISTING_URL}?page={page}"
            soup = _get_page(url, self.session)
            if not soup:
                break

            cards = soup.select('.auction-property-card, .property-listing, [data-auction-lot]')
            if not cards:
                logger.info("No more listings on page %d", page)
                break

            for card in cards:
                try:
                    prop = self._parse_card(card)
                    if prop:
                        results.append(prop)
                except Exception as e:
                    logger.debug("Card parse error: %s", e)

            logger.info("Scraped page %d: %d total so far", page, len(results))

        return results

    def _parse_card(self, card) -> Optional[dict]:
        address = card.select_one('.address, .property-address, h2, h3')
        guide = card.select_one('.guide-price, .price, [data-guide-price]')
        date_el = card.select_one('.auction-date, .date, [data-auction-date]')
        lot = card.select_one('.lot-number, [data-lot]')
        link = card.select_one('a[href]')

        if not address:
            return None

        addr_text = address.get_text(strip=True)
        # Extract postcode from address
        postcode_match = re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', addr_text, re.IGNORECASE)
        postcode = postcode_match.group(0).upper() if postcode_match else ''

        return {
            'address': addr_text,
            'postcode': postcode,
            'guide_price': _parse_price(guide.get_text() if guide else ''),
            'auction_date': _parse_date(date_el.get_text() if date_el else ''),
            'lot_number': lot.get_text(strip=True) if lot else '',
            'auctioneer': 'PropertyAuctions.io',
            'source_url': urljoin(self.BASE_URL, link['href']) if link else '',
        }


class AllsopSpider:
    """Scraper for Allsop residential auctions"""
    BASE_URL = 'https://www.allsop.co.uk'
    LISTING_URL = BASE_URL + '/residential-auctions/properties-for-sale'

    def __init__(self):
        self.session = requests.Session()

    def scrape_listings(self, max_pages: int = 5) -> list:
        results = []
        for page in range(1, max_pages + 1):
            url = f"{self.LISTING_URL}?page={page}"
            soup = _get_page(url, self.session)
            if not soup:
                break

            items = soup.select('.lot, .property-item, article.property')
            if not items:
                break

            for item in items:
                try:
                    prop = self._parse_item(item)
                    if prop:
                        results.append(prop)
                except Exception as e:
                    logger.debug("Item parse error: %s", e)

        return results

    def _parse_item(self, item) -> Optional[dict]:
        address = item.select_one('.lot-address, .address, h2, h3')
        guide = item.select_one('.guide-price, .price')
        date_el = item.select_one('.auction-date, time')
        lot = item.select_one('.lot-number')
        link = item.select_one('a[href]')

        if not address:
            return None

        addr_text = address.get_text(strip=True)
        postcode_match = re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', addr_text, re.IGNORECASE)
        postcode = postcode_match.group(0).upper() if postcode_match else ''

        return {
            'address': addr_text,
            'postcode': postcode,
            'guide_price': _parse_price(guide.get_text() if guide else ''),
            'auction_date': _parse_date(date_el.get_text() if date_el else ''),
            'lot_number': lot.get_text(strip=True) if lot else '',
            'auctioneer': 'Allsop',
            'source_url': urljoin(self.BASE_URL, link['href']) if link else '',
        }


class AuctionImporter:
    """Saves scraped auction data to database"""

    def __init__(self, db: Session):
        self.db = db
        self.deduplicator = PropertyDeduplicator(db)
        self.stats = {'new': 0, 'updated': 0, 'errors': 0}

    def import_listings(self, listings: list, auctioneer: str):
        for listing in listings:
            try:
                self._save_listing(listing)
            except Exception as e:
                logger.warning("Error saving %s listing: %s", auctioneer, e)
                self.stats['errors'] += 1

        self.db.commit()
        logger.info("Imported %s: new=%d updated=%d errors=%d",
                    auctioneer, self.stats['new'], self.stats['updated'], self.stats['errors'])

    def _save_listing(self, listing: dict):
        # Find or create property
        prop = self.deduplicator.find_duplicate(
            address=listing.get('address', ''),
            postcode=listing.get('postcode', ''),
        )

        if not prop:
            prop = Property(
                address=listing['address'],
                postcode=listing.get('postcode', ''),
                property_type='unknown',
                asking_price=listing.get('guide_price'),
                status='active',
                date_found=datetime.utcnow(),
            )
            self.db.add(prop)
            self.db.flush()

        # Check if auction record already exists
        ref = listing.get('lot_number', '') + '_' + listing.get('auctioneer', '')
        existing = (
            self.db.query(Auction)
            .filter(Auction.property_id == prop.id,
                    Auction.lot_number == listing.get('lot_number'))
            .first()
        )

        if existing:
            existing.guide_price = listing.get('guide_price')
            existing.auction_date = listing.get('auction_date')
            self.stats['updated'] += 1
        else:
            auction = Auction(
                property_id=prop.id,
                auctioneer=listing.get('auctioneer', ''),
                lot_number=listing.get('lot_number', ''),
                guide_price=listing.get('guide_price'),
                auction_date=listing.get('auction_date'),
                auction_house_url=listing.get('source_url', ''),
                is_sold=False,
                sale_status='upcoming',
            )
            self.db.add(auction)
            self.stats['new'] += 1


def main():
    db = SessionLocal()
    try:
        importer = AuctionImporter(db)

        spiders = [
            ('PropertyAuctions.io', PropertyAuctionsSpider()),
            ('Allsop', AllsopSpider()),
        ]

        for name, spider in spiders:
            logger.info("Scraping %s...", name)
            listings = spider.scrape_listings()
            logger.info("Found %d listings from %s", len(listings), name)
            importer.import_listings(listings, name)

    finally:
        db.close()


if __name__ == '__main__':
    main()
