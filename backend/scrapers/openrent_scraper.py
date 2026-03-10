"""
OpenRent whole-property rental scraper.
OpenRent is a JS SPA — raw HTML has no listings, so we use Playwright.

Check robots.txt / ToS before running in production. OpenRent does not explicitly
prohibit scraping for non-commercial research in the way Rightmove does, but use
responsibly: rate-limit requests and identify your client.

Run:
    python -m backend.scrapers.openrent_scraper NG1 NG2 NG7 --pages 3
    python -m backend.scrapers.openrent_scraper --districts-from-db --pages 5
"""
import asyncio
import logging
import os
import random
import re
import sys
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.rental import Rental
from backend.models.property import Property

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r'[£,\s]', '', text)
    m = re.search(r'\d+', cleaned)
    if not m:
        return None
    price = float(m.group(0))
    if re.search(r'p[. ]?c[. ]?w|per week|/week', text, re.IGNORECASE):
        price = price * 52 / 12
    return price


def _extract_postcode(text: str) -> str:
    m = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', text, re.IGNORECASE)
    return m.group(1).upper().strip() if m else ''


class OpenRentScraper:
    """
    Scrapes OpenRent.co.uk for whole-property to-rent listings using Playwright.
    OpenRent is a JS SPA — requests/BeautifulSoup returns no listings.
    """
    BASE = 'https://www.openrent.co.uk'
    SEARCH = BASE + '/properties-to-rent/'

    # Delay between districts — OpenRent rate-limits at ~1 req/2s; 429 = 90s cooldown
    DISTRICT_DELAY = (10, 20)  # seconds between districts
    RATE_LIMIT_BACKOFF = 100   # seconds to wait on 429

    async def scrape_district(self, district: str, max_pages: int = 5) -> list[dict]:
        """Scrape all listings in a postcode district (e.g. 'NG1')."""
        from playwright.async_api import async_playwright
        listings = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
            })
            try:
                for pg in range(1, max_pages + 1):
                    url = f"{self.SEARCH}?term={district}&isLive=1&page={pg}"
                    try:
                        resp = await page.goto(url, wait_until='networkidle', timeout=30000)
                    except Exception as e:
                        logger.warning('OpenRent navigation failed for %s page %d: %s', district, pg, e)
                        break

                    # Detect rate limit (429 or "wait N seconds" page)
                    status = resp.status if resp else 200
                    if status == 429:
                        logger.warning('OpenRent rate limited on %s — waiting %ds', district, self.RATE_LIMIT_BACKOFF)
                        await asyncio.sleep(self.RATE_LIMIT_BACKOFF)
                        resp = await page.goto(url, wait_until='networkidle', timeout=30000)
                    body_text = await page.inner_text('body')
                    if 'wait' in body_text[:100].lower() and 'seconds' in body_text[:100].lower():
                        logger.warning('OpenRent throttle page on %s — waiting %ds', district, self.RATE_LIMIT_BACKOFF)
                        await asyncio.sleep(self.RATE_LIMIT_BACKOFF)
                        await page.goto(url, wait_until='networkidle', timeout=30000)

                    # OpenRent uses .pli for property listing cards (as of 2026)
                    cards = await page.query_selector_all('.pli')
                    if not cards:
                        cards = await page.query_selector_all(
                            '.property-listing, [data-property-id], '
                            'li.listing, div.listing, article[data-listing-id]'
                        )
                    if not cards:
                        cards = await page.query_selector_all('a[href*="/property/"]')

                    if not cards:
                        logger.info('OpenRent %s page %d: no listings found, stopping', district, pg)
                        break

                    for card in cards:
                        try:
                            item = await self._parse_card(card, district)
                            if item:
                                listings.append(item)
                        except Exception as e:
                            logger.debug('Parse error: %s', e)

                    logger.info('OpenRent %s page %d: %d total so far', district, pg, len(listings))
                    await asyncio.sleep(random.uniform(4, 8))
            finally:
                await browser.close()
        return listings

    async def _parse_card(self, card, fallback_district: str) -> Optional[dict]:
        text = await card.inner_text()

        # Rent — first £NNN in the text (e.g. "£715\nper month\n...")
        m = re.search(r'£([\d,]+)', text)
        rent = _parse_price(m.group(0)) if m else None
        if not rent or rent < 200:
            return None

        # Bedrooms — "2 Bed ..." or "Studio" = 0 beds
        beds_m = re.search(r'(\d+)\s*[Bb]ed', text)
        if beds_m:
            bedrooms = int(beds_m.group(1))
        elif re.search(r'\bstudio\b', text, re.IGNORECASE):
            bedrooms = 0
        else:
            bedrooms = None

        # Property type
        type_m = re.search(
            r'\b(flat|apartment|studio|terraced|semi.detached|detached|bungalow|maisonette|house)\b',
            text, re.IGNORECASE
        )
        property_type = type_m.group(1).lower() if type_m else None
        if property_type == 'apartment':
            property_type = 'flat'
        if property_type and 'semi' in property_type:
            property_type = 'semi-detached'

        # Postcode — full postcode rarely present; fall back to district
        postcode = _extract_postcode(text) or fallback_district

        # Source URL — built from data-listing-id on the inner swiper element
        swiper = await card.query_selector('[data-listing-id]')
        lid = (await swiper.get_attribute('data-listing-id')) if swiper else None
        source_url = f'{self.BASE}/properties/{lid}' if lid else ''

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
                try:
                    self.db.rollback()
                except Exception:
                    pass
                self.stats['errors'] += 1

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
        """Create/update median rent aggregates per district+bedrooms."""
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

        by_beds: dict[Optional[int], list[float]] = {}
        for r in rows:
            by_beds.setdefault(r.bedrooms, []).append(r.rent_monthly)

        for beds, rents in by_beds.items():
            if not rents:
                continue
            median_rent = sorted(rents)[len(rents) // 2]

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
            {str(b) + 'bd': round(sorted(r)[len(r) // 2]) for b, r in by_beds.items()}
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
        for i, district in enumerate(districts):
            logger.info('Scraping district %s (%d/%d)...', district, i + 1, len(districts))
            listings = asyncio.run(scraper.scrape_district(district, max_pages=args.pages))
            logger.info('%s: %d listings found', district, len(listings))
            all_listings.extend(listings)
            if i < len(districts) - 1:
                delay = random.uniform(*OpenRentScraper.DISTRICT_DELAY)
                logger.info('Waiting %.0fs before next district...', delay)
                import time; time.sleep(delay)

        logger.info('Total listings scraped: %d', len(all_listings))
        importer.import_listings(all_listings)
        logger.info('Import complete: %s', importer.stats)
    finally:
        db.close()


if __name__ == '__main__':
    main()
