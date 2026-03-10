"""
Rightmove whole-property rental scraper.

Rightmove prohibits scraping in its ToS — use only for authorised research/testing.
Two-step approach:
  1. Resolve postcode district → Rightmove OUTCODE ID via their typeahead API (plain HTTP).
  2. Fetch rental search pages with Playwright (JS-rendered results).

Run:
    python -m backend.scrapers.rightmove_rental_scraper NG1 NG7 LS1 --pages 3
    python -m backend.scrapers.rightmove_rental_scraper --districts-from-db --pages 5
"""
import asyncio
import logging
import os
import random
import re
import sys
from datetime import date
from typing import Optional

import requests
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.rental import Rental
from backend.models.property import Property

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-GB,en;q=0.9',
}


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r'[£,\s]', '', text)
    m = re.search(r'\d+', cleaned)
    if not m:
        return None
    price = float(m.group(0))
    # pcm / per month already; convert pw → pcm
    if re.search(r'p[. ]?w|per week|/week', text, re.IGNORECASE):
        price = price * 52 / 12
    return price


def _extract_postcode(text: str) -> str:
    m = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', text, re.IGNORECASE)
    return m.group(1).upper().strip() if m else ''


class RightmoveRentalScraper:
    """
    Scrapes Rightmove property-to-rent search using Playwright.
    Resolves district → OUTCODE ID via typeahead, then paginates results.
    """
    # Rightmove Location Outcode Service (found via browser network intercept)
    TYPEAHEAD = 'https://los.rightmove.co.uk/typeahead'
    SEARCH = 'https://www.rightmove.co.uk/property-to-rent/find.html'
    BASE = 'https://www.rightmove.co.uk'

    def resolve_location_id(self, district: str) -> Optional[str]:
        """Get Rightmove OUTCODE^ID identifier for a postcode district."""
        try:
            r = requests.get(
                self.TYPEAHEAD,
                params={'query': district, 'limit': 10, 'exclude': 'STREET'},
                headers=HEADERS,
                timeout=10,
            )
            r.raise_for_status()
            matches = r.json().get('matches', [])
            for m in matches:
                if m.get('type') == 'OUTCODE' and m.get('displayName', '').upper() == district.upper():
                    loc_id = f"OUTCODE^{m['id']}"
                    logger.debug('Resolved %s → %s', district, loc_id)
                    return loc_id
            # Fallback: first OUTCODE match
            for m in matches:
                if m.get('type') == 'OUTCODE':
                    loc_id = f"OUTCODE^{m['id']}"
                    logger.debug('Resolved %s → %s (fallback)', district, loc_id)
                    return loc_id
        except Exception as e:
            logger.warning('Typeahead lookup failed for %s: %s', district, e)
        return None

    async def scrape_district(self, district: str, max_pages: int = 5) -> list[dict]:
        """Scrape rental listings for a postcode district (e.g. 'NG1')."""
        loc_id = self.resolve_location_id(district)
        if not loc_id:
            logger.warning('Could not resolve Rightmove location ID for %s — skipping', district)
            return []

        from playwright.async_api import async_playwright
        listings = []
        seen_urls: set = set()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers(HEADERS)
            try:
                for pg in range(max_pages):
                    url = (
                        f"{self.SEARCH}"
                        f"?locationIdentifier={loc_id}"
                        f"&sortType=2"
                        f"&index={pg * 24}"
                        f"&propertyTypes=&mustHave=&dontShow=&furnishTypes=&keywords="
                    )
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=30000)
                    except Exception as e:
                        logger.warning('Rightmove navigation failed for %s page %d: %s', district, pg + 1, e)
                        break

                    # Rightmove uses .propertyCard-details as the stable card class (2026)
                    cards = await page.query_selector_all('.propertyCard-details')

                    if not cards:
                        logger.info('Rightmove %s page %d: no listings found, stopping', district, pg + 1)
                        break

                    new_count = 0
                    for card in cards:
                        try:
                            item = await self._parse_card(card, district)
                            if item:
                                url_key = item.get('source_url', '')
                                if url_key and url_key in seen_urls:
                                    continue  # duplicate — already seen on a prior page
                                if url_key:
                                    seen_urls.add(url_key)
                                listings.append(item)
                                new_count += 1
                        except Exception as e:
                            logger.debug('Parse error: %s', e)

                    logger.info('Rightmove %s page %d: %d new, %d total', district, pg + 1, new_count, len(listings))
                    if new_count == 0:
                        logger.info('Rightmove %s: no new results on page %d — stopping early', district, pg + 1)
                        break
                    await asyncio.sleep(random.uniform(2, 4))
            finally:
                await browser.close()
        return listings

    async def _parse_card(self, card, fallback_district: str) -> Optional[dict]:
        text = await card.inner_text()

        # Rent — "£872 pcm" is the monthly figure; skip weekly "pw" entries
        m = re.search(r'£([\d,]+)\s*pcm', text)
        if not m:
            m = re.search(r'£([\d,]+)', text)
        rent = _parse_price(m.group(0)) if m else None
        if not rent or rent < 200:
            return None

        # Bedrooms — text layout: TYPE\nN_BEDS\nN_BATHS; first standalone int after type
        beds_m = re.search(r'(\d+)\s*(?:bed|bedroom|bd)', text, re.IGNORECASE)
        if beds_m:
            bedrooms = int(beds_m.group(1))
        else:
            # Fallback: first isolated number on its own line after the address
            lines = [l.strip() for l in text.splitlines() if l.strip().isdigit()]
            bedrooms = int(lines[0]) if lines else None

        # Property type
        type_m = re.search(
            r'\b(flat|apartment|studio|terraced|semi.detached|semi-detached|detached|bungalow|maisonette|house)\b',
            text, re.IGNORECASE
        )
        property_type = type_m.group(1).lower() if type_m else None
        if property_type == 'apartment':
            property_type = 'flat'
        if property_type and 'semi' in property_type:
            property_type = 'semi-detached'

        # Postcode — full postcode is in the address line
        postcode = _extract_postcode(text) or fallback_district

        # Source URL
        link_el = await card.query_selector('a[href*="/properties/"]')
        href = (await link_el.get_attribute('href')) if link_el else None
        source_url = (self.BASE + href.split('#')[0]) if href and href.startswith('/') else (href or '')

        return {
            'postcode': postcode,
            'rent_monthly': rent,
            'bedrooms': bedrooms,
            'property_type': property_type,
            'source': 'rightmove',
            'source_url': source_url,
            'is_hmo': False,
            'date_listed': date.today(),
        }


class RightmoveRentalImporter:
    """Saves Rightmove listings and creates per-district-bedrooms aggregates."""

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
                    source='rightmove_aggregate',
                ))
            self.stats['aggregated'] += 1

        logger.info(
            'Rightmove aggregates for %s: %s',
            district,
            {str(b) + 'bd': round(sorted(r)[len(r) // 2]) for b, r in by_beds.items()}
        )


def get_active_districts(db: Session) -> list[str]:
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
    parser = argparse.ArgumentParser(description='Scrape Rightmove for whole-property rental data')
    parser.add_argument(
        'districts', nargs='*',
        help='Postcode districts to scrape (e.g. NG1 NG7 LS1). Omit to use --districts-from-db.'
    )
    parser.add_argument(
        '--districts-from-db', action='store_true',
        help='Automatically scrape all postcode districts that have active properties in DB'
    )
    parser.add_argument('--pages', type=int, default=5, help='Max pages per district (default 5)')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        scraper = RightmoveRentalScraper()
        importer = RightmoveRentalImporter(db)

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
            listings = asyncio.run(scraper.scrape_district(district, max_pages=args.pages))
            logger.info('%s: %d listings found', district, len(listings))
            all_listings.extend(listings)

        logger.info('Total listings scraped: %d', len(all_listings))
        importer.import_listings(all_listings)
        logger.info('Import complete: %s', importer.stats)
    finally:
        db.close()


if __name__ == '__main__':
    main()
