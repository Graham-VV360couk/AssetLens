"""
Zoopla for-sale property scraper.

Scrapes Zoopla for-sale listings using Playwright (JS-rendered pages).
Zoopla's robots.txt does not explicitly block for-sale listing pages.

Two modes:
  1. By postcode district: scrape all for-sale in e.g. WD25, NG1
  2. From DB: scrape districts where we already have active properties

Run:
    python -m backend.scrapers.zoopla_scraper WD25 NG1 LS1 --pages 5
    python -m backend.scrapers.zoopla_scraper --districts-from-db --pages 3
"""
import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.models.base import SessionLocal
from backend.models.property import Property, PropertySource

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-GB,en;q=0.9',
}

# Rotating user agents to vary browser fingerprint across sessions
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
]

# Proxy configuration: set ZOOPLA_PROXY_URL in .env
# Format: http://user:pass@host:port or socks5://host:port
# For rotating residential proxies, providers like BrightData, Oxylabs, SmartProxy
PROXY_URL = os.environ.get('ZOOPLA_PROXY_URL', '')


def _parse_price(text: str) -> Optional[float]:
    """Extract price from text like '£275,000' or 'Guide Price: £150,000'."""
    if not text:
        return None
    cleaned = re.sub(r'[£,\s]', '', text)
    m = re.search(r'\d+', cleaned)
    return float(m.group(0)) if m else None


def _extract_postcode(text: str) -> str:
    """Extract full UK postcode from text."""
    m = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', text, re.IGNORECASE)
    return m.group(1).upper().strip() if m else ''


def _extract_beds(text: str) -> Optional[int]:
    m = re.search(r'(\d+)\s*(?:bed|bedroom|bd)', text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_baths(text: str) -> Optional[int]:
    m = re.search(r'(\d+)\s*(?:bath|bathroom)', text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_receptions(text: str) -> Optional[int]:
    m = re.search(r'(\d+)\s*(?:reception|living)', text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_property_type(text: str) -> Optional[str]:
    m = re.search(
        r'\b(flat|apartment|studio|terraced|terrace|semi.detached|semi-detached|'
        r'detached|bungalow|maisonette|house|cottage|end.of.terrace|town.house|'
        r'penthouse|park home|land|farm|barn)\b',
        text, re.IGNORECASE
    )
    if not m:
        return None
    t = m.group(1).lower()
    if t in ('apartment', 'penthouse'):
        return 'flat'
    if 'semi' in t:
        return 'semi-detached'
    if t in ('terrace', 'terraced', 'end of terrace'):
        return 'terraced'
    if t in ('town house',):
        return 'terraced'
    if t in ('cottage', 'farm', 'barn'):
        return 'detached'
    return t


def _extract_price_qualifier(text: str) -> Optional[str]:
    """Extract qualifier like 'Guide price', 'Offers over', etc."""
    m = re.search(
        r'(guide price|offers? (?:over|in excess of|in the region of)|'
        r'from|price on application|poa|fixed price|shared ownership)',
        text, re.IGNORECASE
    )
    return m.group(1).lower() if m else None


class ZooplaScraper:
    """
    Scrapes Zoopla for-sale search pages using Playwright.
    Designed to mimic realistic human browsing behaviour:
    - Gradual scrolling with random pauses
    - Mouse movement and hover events
    - Realistic page dwell times (15-30s per page)
    - Warm-up via homepage before searching
    - Random inter-page delays (10-25s)
    - Long inter-district delays (30-90s)
    - Max 5-8 districts per session (like a real user)
    """
    BASE = 'https://www.zoopla.co.uk'

    # Human-speed delays (seconds)
    PAGE_DWELL = (15, 30)         # time spent "reading" a results page
    PAGE_DELAY = (10, 25)         # pause between clicking next page
    DISTRICT_DELAY = (30, 90)     # pause between searching new districts
    SCROLL_PAUSE = (0.5, 2.0)    # pause between scroll steps
    MAX_DISTRICTS_PER_SESSION = 8 # a real user doesn't search 50 areas in one sitting

    async def _human_scroll(self, page):
        """Scroll down the page gradually like a human reading listings."""
        viewport_height = 1080
        page_height = await page.evaluate('document.body.scrollHeight')
        current = 0
        while current < page_height - viewport_height:
            # Scroll a random amount (200-500px), like reading a card or two
            scroll_amount = random.randint(200, 500)
            current = min(current + scroll_amount, page_height - viewport_height)
            await page.evaluate(f'window.scrollTo(0, {current})')
            await asyncio.sleep(random.uniform(*self.SCROLL_PAUSE))

    async def _human_mouse_move(self, page):
        """Move mouse to a random position on the page, like a real user."""
        x = random.randint(200, 1200)
        y = random.randint(200, 800)
        await page.mouse.move(x, y, steps=random.randint(5, 15))

    async def _dismiss_cookies(self, page):
        """Dismiss Zoopla cookie consent overlay."""
        try:
            await page.evaluate(
                'document.querySelector("#usercentrics-cmp-ui")?.remove()'
            )
        except Exception:
            pass

    async def _warmup(self, page):
        """Visit the homepage first like a real user arriving at the site."""
        logger.info('Warming up — visiting homepage...')
        await page.goto(f'{self.BASE}/', wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(random.uniform(2, 5))
        await self._dismiss_cookies(page)
        await self._human_mouse_move(page)
        await asyncio.sleep(random.uniform(1, 3))

    async def scrape_district(self, district: str, max_pages: int = 5,
                               page=None, browser=None, is_warm: bool = False) -> list[dict]:
        """Scrape all for-sale listings in a postcode district."""
        from playwright.async_api import async_playwright

        listings = []
        seen_urls: set = set()
        own_browser = browser is None

        pw = None
        if own_browser:
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled'],
            )
            context = await browser.new_context(
                user_agent=HEADERS['User-Agent'],
                locale='en-GB',
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True,
            )
            page = await context.new_page()
            await page.add_init_script('''
                Object.defineProperty(navigator, "webdriver", {get: () => undefined});
                Object.defineProperty(navigator, "plugins", {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, "languages", {get: () => ["en-GB", "en"]});
                window.chrome = { runtime: {} };
            ''')

        try:
            if not is_warm:
                await self._warmup(page)

            for pg in range(1, max_pages + 1):
                # Clean URL on page 1 (like typing it in), pagination only on subsequent
                if pg == 1:
                    url = f"{self.BASE}/for-sale/property/{district.lower()}/"
                else:
                    url = f"{self.BASE}/for-sale/property/{district.lower()}/?pn={pg}"

                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                    await self._dismiss_cookies(page)

                    if response and response.status == 403:
                        logger.warning('Zoopla 403 for %s — backing off 2 minutes', district)
                        await asyncio.sleep(120)
                        break
                    if response and response.status == 404:
                        logger.info('Zoopla 404 for %s — no results', district)
                        break
                except Exception as e:
                    logger.warning('Navigation failed for %s page %d: %s', district, pg, e)
                    break

                # Wait for page to render, then scroll like a human reading
                await page.wait_for_timeout(random.randint(2000, 4000))
                try:
                    await page.wait_for_selector('a[href*="/for-sale/details/"]', timeout=10000)
                except Exception:
                    logger.info('Zoopla %s page %d: no results found', district, pg)
                    break

                # Human-like: move mouse, then scroll through listings
                await self._human_mouse_move(page)
                await self._human_scroll(page)

                # Extract listings
                new_listings = await self._extract_listings(page, district, seen_urls)

                if not new_listings:
                    logger.info('Zoopla %s page %d: no new listings, stopping', district, pg)
                    break

                listings.extend(new_listings)
                logger.info('Zoopla %s page %d: %d new, %d total', district, pg, len(new_listings), len(listings))

                # Check for next page
                next_btn = await page.query_selector('[data-testid="pagination-next"]')
                if not next_btn:
                    next_btn = await page.query_selector('a[aria-label="Next page"]')
                if not next_btn:
                    logger.info('Zoopla %s: no more pages after %d', district, pg)
                    break

                # Human-speed delay before next page
                delay = random.uniform(*self.PAGE_DELAY)
                logger.debug('Waiting %.1fs before next page...', delay)
                await asyncio.sleep(delay)

        finally:
            if own_browser:
                await browser.close()
                if pw:
                    await pw.stop()

        return listings

    async def _extract_listings(self, page, district: str, seen_urls: set) -> list[dict]:
        """Extract listing data from the current search results page."""
        listings = []

        # Try to get listings from structured data (JSON-LD) first
        json_ld = await self._try_json_ld(page)
        if json_ld:
            for item in json_ld:
                url = item.get('url', '')
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                listings.append(item)
            return listings

        # Fallback: parse DOM elements
        # Zoopla wraps each listing in a div inside [data-testid="regular-listings"]
        cards = await page.query_selector_all('[data-testid="regular-listings"] > div')
        if not cards:
            cards = await page.query_selector_all('[data-testid="search-result"]')
        if not cards:
            # Last resort: find all divs that contain a detail link
            all_links = await page.query_selector_all('a[href*="/for-sale/details/"]')
            # Group by parent — each listing card has one main link
            seen_parents = set()
            cards = []
            for link in all_links:
                parent = await link.evaluate_handle('el => el.closest("div[class]")')
                pid = await parent.evaluate('el => el.className')
                if pid not in seen_parents:
                    seen_parents.add(pid)
                    cards.append(await parent.as_element())

        for card in cards:
            try:
                item = await self._parse_card(card, district)
                if item:
                    url_key = item.get('source_url', '')
                    if url_key and url_key in seen_urls:
                        continue
                    if url_key:
                        seen_urls.add(url_key)
                    listings.append(item)
            except Exception as e:
                logger.debug('Parse error: %s', e)

        return listings

    async def _try_json_ld(self, page) -> list[dict]:
        """Try to extract structured listing data from JSON-LD scripts."""
        try:
            scripts = await page.query_selector_all('script[type="application/ld+json"]')
            for script in scripts:
                content = await script.inner_text()
                data = json.loads(content)
                if isinstance(data, dict) and data.get('@type') == 'ItemList':
                    items = data.get('itemListElement', [])
                    results = []
                    for item in items:
                        thing = item.get('item', item)
                        if thing.get('@type') in ('Residence', 'House', 'Apartment', 'Product'):
                            address = thing.get('address', {})
                            results.append({
                                'address': thing.get('name', ''),
                                'postcode': address.get('postalCode', ''),
                                'asking_price': _parse_price(str(thing.get('offers', {}).get('price', ''))),
                                'source_url': thing.get('url', ''),
                            })
                    if results:
                        return results
        except Exception:
            pass
        return []

    async def _parse_card(self, card, fallback_district: str) -> Optional[dict]:
        """Parse a single listing card element."""
        text = await card.inner_text()
        if not text or len(text) < 20:
            return None

        # Price
        price = _parse_price(text)
        if not price or price < 10000:
            return None

        # Address — look for lines containing street/place patterns
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        address = ''
        for line in lines:
            # Skip obvious non-address lines
            if line.startswith('£') or line.startswith('$'):
                continue
            if re.match(r'^[\d,/]+$', line):
                continue
            if len(line) < 5 or len(line) > 150:
                continue
            lower = line.lower()
            if lower in ('see monthly cost', 'new', 'premium listing', 'featured',
                         'property of the week', 'save', 'email', 'hide'):
                continue
            if re.match(r'^\d+\s*bed', lower):
                continue
            if lower.startswith('guide price') or lower.startswith('offers'):
                continue
            if lower.startswith('premium'):
                continue
            # Looks like an address if it contains a road/place keyword or a postcode
            if re.search(r'\b(road|street|lane|drive|close|avenue|way|crescent|'
                         r'gardens|terrace|place|court|mews|hill|park|grove|'
                         r'square|row|[A-Z]{1,2}\d)\b', line, re.IGNORECASE):
                address = line
                break
        # Fallback: take longest non-price line
        if not address:
            candidates = [l for l in lines
                          if not l.startswith('£') and len(l) > 10 and not re.match(r'^\d', l)]
            if candidates:
                address = max(candidates, key=len)

        # Postcode
        postcode = _extract_postcode(text) or fallback_district

        # Property details
        bedrooms = _extract_beds(text)
        bathrooms = _extract_baths(text)
        reception_rooms = _extract_receptions(text)
        property_type = _extract_property_type(text)
        price_qualifier = _extract_price_qualifier(text)

        # Source URL
        link = await card.query_selector('a[href*="/for-sale/details/"]')
        if not link:
            link = await card.query_selector('a[href*="/details/"]')
        href = (await link.get_attribute('href')) if link else None
        source_url = ''
        if href:
            source_url = href if href.startswith('http') else self.BASE + href
            source_url = source_url.split('?')[0]  # strip query params

        # Image
        img = await card.query_selector('img[src*="lc.zoocdn"]')
        if not img:
            img = await card.query_selector('img[src*="zoopla"]')
        image_url = (await img.get_attribute('src')) if img else None

        # Extract Zoopla listing ID from URL
        source_id = ''
        if source_url:
            m = re.search(r'/details/(\d+)', source_url)
            source_id = m.group(1) if m else ''

        return {
            'address': address,
            'postcode': postcode,
            'asking_price': price,
            'price_qualifier': price_qualifier,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'reception_rooms': reception_rooms,
            'property_type': property_type,
            'source_url': source_url,
            'source_id': source_id,
            'image_url': image_url,
            'description': None,  # fetched on detail page if needed
        }


class ZooplaImporter:
    """Saves Zoopla listings into the properties table with deduplication."""

    def __init__(self, db: Session):
        self.db = db
        self.stats = {'new': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

    def import_listings(self, listings: list[dict], districts_scraped: list[str] = None):
        for listing in listings:
            try:
                self._upsert_listing(listing)
            except Exception as e:
                logger.warning('Error saving listing: %s', e)
                try:
                    self.db.rollback()
                except Exception:
                    pass
                self.stats['errors'] += 1

        # Mark listings not seen in this scrape as no longer active
        if districts_scraped:
            self._mark_stale(listings, districts_scraped)

        self.db.commit()

    def _mark_stale(self, listings: list[dict], districts: list[str]):
        """
        For scraped districts, mark Zoopla listings not seen in this run as stale.
        Properties go from 'active' to 'stc' (assumed sold/withdrawn).
        We never delete — historical data is valuable.
        """
        seen_ids = {l.get('source_id') for l in listings if l.get('source_id')}

        for district in districts:
            # Find all active Zoopla properties in this district
            active_sources = (
                self.db.query(PropertySource)
                .join(Property, Property.id == PropertySource.property_id)
                .filter(
                    PropertySource.source_name == 'zoopla',
                    PropertySource.is_active == True,
                    Property.status == 'active',
                    Property.postcode.ilike(f'{district}%'),
                )
                .all()
            )

            stale_count = 0
            for source in active_sources:
                if source.source_id and source.source_id not in seen_ids:
                    source.is_active = False
                    source.property.status = 'stc'
                    stale_count += 1

            if stale_count:
                logger.info('%s: marked %d listings as no longer active', district, stale_count)
                self.stats['stale'] = self.stats.get('stale', 0) + stale_count

    def _upsert_listing(self, data: dict):
        source_id = data.get('source_id', '')
        source_url = data.get('source_url', '')

        if not source_id and not source_url:
            self.stats['skipped'] += 1
            return

        # Check if we already have this listing
        existing_source = None
        if source_id:
            existing_source = (
                self.db.query(PropertySource)
                .filter(PropertySource.source_name == 'zoopla', PropertySource.source_id == source_id)
                .first()
            )

        if existing_source:
            # Update last_seen_at
            existing_source.last_seen_at = datetime.utcnow()
            # Update price if changed
            prop = existing_source.property
            if prop and data.get('asking_price') and prop.asking_price != data['asking_price']:
                prop.asking_price = data['asking_price']
                self.stats['updated'] += 1
            else:
                self.stats['skipped'] += 1
            return

        # Create new property
        postcode = data.get('postcode', '').strip().upper()
        if not postcode:
            self.stats['skipped'] += 1
            return

        # Try to extract town from address
        address = data.get('address', '')
        town = None
        parts = [p.strip() for p in address.split(',')]
        if len(parts) >= 2:
            town = parts[-1] if not re.match(r'^[A-Z]{1,2}\d', parts[-1]) else (parts[-2] if len(parts) > 2 else None)

        prop = Property(
            address=address,
            postcode=postcode,
            town=town,
            property_type=data.get('property_type') or 'other',
            bedrooms=data.get('bedrooms'),
            bathrooms=data.get('bathrooms'),
            reception_rooms=data.get('reception_rooms'),
            asking_price=data.get('asking_price'),
            price_qualifier=data.get('price_qualifier'),
            image_url=data.get('image_url'),
            description=data.get('description'),
            status='active',
            date_found=date.today(),
        )
        self.db.add(prop)
        self.db.flush()  # get prop.id

        source = PropertySource(
            property_id=prop.id,
            source_name='zoopla',
            source_id=source_id,
            source_url=source_url,
            is_active=True,
        )
        self.db.add(source)
        self.stats['new'] += 1


def get_active_districts(db: Session) -> list[str]:
    """Get unique postcode districts from active properties."""
    rows = (
        db.query(Property.postcode)
        .filter(Property.status == 'active', Property.postcode.isnot(None), Property.postcode != '')
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
    return sorted(districts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scrape Zoopla for-sale listings')
    parser.add_argument(
        'districts', nargs='*',
        help='Postcode districts to scrape (e.g. WD25 NG1 LS1)'
    )
    parser.add_argument(
        '--districts-from-db', action='store_true',
        help='Scrape all districts that have active properties in DB'
    )
    parser.add_argument('--pages', type=int, default=5, help='Max pages per district (default 5)')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        scraper = ZooplaScraper()
        importer = ZooplaImporter(db)

        districts = list(args.districts)
        if args.districts_from_db or not districts:
            db_districts = get_active_districts(db)
            logger.info('Found %d districts in DB: %s...', len(db_districts), db_districts[:20])
            districts = districts + [d for d in db_districts if d not in districts]

        if not districts:
            logger.error('No districts specified and none found in DB.')
            return

        # Limit districts per session to look like a real user
        if len(districts) > scraper.MAX_DISTRICTS_PER_SESSION:
            logger.info(
                'Limiting to %d districts per session (of %d total). '
                'Run again for the next batch.',
                scraper.MAX_DISTRICTS_PER_SESSION, len(districts),
            )
            # Shuffle so we don't always scrape the same ones first
            random.shuffle(districts)
            districts = districts[:scraper.MAX_DISTRICTS_PER_SESSION]

        logger.info('Scraping %d districts: %s', len(districts), districts)

        async def _run_session():
            from playwright.async_api import async_playwright
            all_listings = []

            ua = random.choice(USER_AGENTS)
            logger.info('Session user-agent: %s', ua[:50])

            async with async_playwright() as pw:
                launch_args = {
                    'headless': True,
                    'args': ['--disable-blink-features=AutomationControlled'],
                }
                # Add proxy if configured
                # Supports http://user:pass@host:port format
                if PROXY_URL:
                    from urllib.parse import urlparse
                    parsed = urlparse(PROXY_URL)
                    proxy_conf = {'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}'}
                    if parsed.username:
                        proxy_conf['username'] = parsed.username
                    if parsed.password:
                        proxy_conf['password'] = parsed.password
                    launch_args['proxy'] = proxy_conf
                    logger.info('Using proxy: %s:%s', parsed.hostname, parsed.port)

                browser = await pw.chromium.launch(**launch_args)

                # Randomise viewport slightly — real users have different screen sizes
                width = random.choice([1366, 1440, 1536, 1920])
                height = random.choice([768, 900, 1024, 1080])

                context = await browser.new_context(
                    user_agent=ua,
                    locale='en-GB',
                    viewport={'width': width, 'height': height},
                    timezone_id='Europe/London',
                )
                page = await context.new_page()
                await page.add_init_script('''
                    Object.defineProperty(navigator, "webdriver", {get: () => undefined});
                    Object.defineProperty(navigator, "plugins", {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, "languages", {get: () => ["en-GB", "en"]});
                    window.chrome = { runtime: {} };
                ''')

                # Warm up only if not using a proxy (proxy gives fresh identity)
                if not PROXY_URL:
                    await scraper._warmup(page)
                is_warm = bool(PROXY_URL)

                for i, district in enumerate(districts, 1):
                    logger.info('[%d/%d] Scraping %s...', i, len(districts), district)
                    listings = await scraper.scrape_district(
                        district, max_pages=args.pages,
                        page=page, browser=browser, is_warm=is_warm,
                    )
                    logger.info('%s: %d listings found', district, len(listings))
                    all_listings.extend(listings)

                    if i < len(districts):
                        delay = random.uniform(*scraper.DISTRICT_DELAY)
                        logger.info('Waiting %.0fs before next district (human pace)...', delay)
                        await asyncio.sleep(delay)

                await browser.close()

            return all_listings

        all_listings = asyncio.run(_run_session())

        logger.info('Total listings scraped: %d', len(all_listings))
        importer.import_listings(all_listings, districts_scraped=districts)
        logger.info('Import complete: %s', importer.stats)

    finally:
        db.close()


if __name__ == '__main__':
    main()
