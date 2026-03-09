"""Scraper source management endpoints."""
import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.models.property import Property, PropertyScore
from backend.models.auction import Auction
from backend.models.scraper_source import ScraperSource, ScraperStrategyLibrary
from backend.models.scraper_run_log import ScraperRunLog
from backend.services.scoring_service import PropertyScoringService, save_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/scrapers', tags=['scrapers'])


def _db_log(db: Session, source_id: int, run_id: str, level: str, message: str, run_type: str = 'scrape'):
    """Write a log line to the DB. Commits immediately so it's visible during long runs."""
    try:
        entry = ScraperRunLog(
            source_id=source_id,
            run_id=run_id,
            run_type=run_type,
            level=level,
            message=message[:2000],
            created_at=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

HEADERS = {
    'User-Agent': 'AssetLens/1.0 (property investment research; contact@assetlens.co.uk)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
}
RATE_LIMIT = 2.0

# ---------------------------------------------------------------------------
# PROBE_REGISTRY — built-in strategies to try automatically when auto-detection
# fails. Each entry defines how to test and how to build a strategy dict.
# probe_id keys are stored in scraper_strategy_library for success tracking.
# ---------------------------------------------------------------------------
def _q(url: str, param: str) -> str:
    """Append a query param to a URL cleanly."""
    return url + ('&' if '?' in url else '?') + param

PROBE_REGISTRY = {
    # --- All-results URL probes (single page, no pagination needed) ---
    'allresults_size_500': {
        'name': 'All results (size=500)',
        'description': 'Append ?size=500 to return all listings on one page',
        'type': 'all_results_url',
        'test_url': lambda u: _q(u, 'size=500'),
        'strategy': lambda u: {'type': 'all_results_url', 'all_results_url': _q(u, 'size=500')},
    },
    'allresults_per_page_500': {
        'name': 'All results (per_page=500)',
        'description': 'Append ?per_page=500 to return all listings on one page',
        'type': 'all_results_url',
        'test_url': lambda u: _q(u, 'per_page=500'),
        'strategy': lambda u: {'type': 'all_results_url', 'all_results_url': _q(u, 'per_page=500')},
    },
    'allresults_limit_500': {
        'name': 'All results (limit=500)',
        'description': 'Append ?limit=500 to return all listings on one page',
        'type': 'all_results_url',
        'test_url': lambda u: _q(u, 'limit=500'),
        'strategy': lambda u: {'type': 'all_results_url', 'all_results_url': _q(u, 'limit=500')},
    },
    'allresults_count_500': {
        'name': 'All results (count=500)',
        'description': 'Append ?count=500 to return all listings on one page',
        'type': 'all_results_url',
        'test_url': lambda u: _q(u, 'count=500'),
        'strategy': lambda u: {'type': 'all_results_url', 'all_results_url': _q(u, 'count=500')},
    },
    # --- Pagination template probes (test page 2, derive template) ---
    'query_page': {
        'name': 'Query param (?page=N)',
        'description': 'Generic ?page=N query parameter pagination',
        'type': 'pagination_template',
        'test_url': lambda u: _q(u, 'page=2'),
        'strategy': lambda u: {'type': 'pagination_template', 'pagination_template': {
            'template': _q(u, 'page={page}'), 'start_page': 1, 'step': 1, 'sample_pages': [2],
        }},
    },
    'query_paged': {
        'name': 'Query param (?paged=N)',
        'description': 'WordPress-style ?paged=N pagination',
        'type': 'pagination_template',
        'test_url': lambda u: _q(u, 'paged=2'),
        'strategy': lambda u: {'type': 'pagination_template', 'pagination_template': {
            'template': _q(u, 'paged={page}'), 'start_page': 1, 'step': 1, 'sample_pages': [2],
        }},
    },
    'wp_page_path': {
        'name': 'WordPress /page/N/ path',
        'description': 'WordPress /page/N/ URL path pagination',
        'type': 'pagination_template',
        'test_url': lambda u: u.rstrip('/') + '/page/2/',
        'strategy': lambda u: {'type': 'pagination_template', 'pagination_template': {
            'template': u.rstrip('/') + '/page/{page}/', 'start_page': 1, 'step': 1, 'sample_pages': [2],
        }},
    },
    'numbered_path': {
        'name': 'Numbered path segment (/N/)',
        'description': 'URL path ends with a page number: /listings/2/',
        'type': 'pagination_template',
        'test_url': lambda u: u.rstrip('/') + '/2/',
        'strategy': lambda u: {'type': 'pagination_template', 'pagination_template': {
            'template': u.rstrip('/') + '/{page}/', 'start_page': 1, 'step': 1, 'sample_pages': [2],
        }},
    },
    'query_offset_20': {
        'name': 'Offset pagination (?offset=N, step 20)',
        'description': 'Pagination by offset: ?offset=20, ?offset=40, etc.',
        'type': 'pagination_template',
        'test_url': lambda u: _q(u, 'offset=20'),
        'strategy': lambda u: {'type': 'pagination_template', 'pagination_template': {
            'template': _q(u, 'offset={page}'), 'start_page': 0, 'step': 20, 'sample_pages': [20],
        }},
    },
}


# --- Schemas ---

class ScraperSourceCreate(BaseModel):
    name: str
    url: str
    source_type: str = 'auction'
    max_pages: int = 5
    notes: Optional[str] = None
    scrape_detail_pages: bool = False


class ScraperSourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    max_pages: Optional[int] = None
    notes: Optional[str] = None
    scrape_detail_pages: Optional[bool] = None


class ScraperHint(BaseModel):
    """User-provided hints to resolve pagination when auto-detection fails."""
    page_urls: Optional[List[str]] = None       # 2+ sample page URLs → derive template
    all_results_url: Optional[str] = None        # URL returning all results on one page


class ScraperSourceResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: str
    is_active: bool
    max_pages: int
    notes: Optional[str]
    scrape_detail_pages: Optional[bool]
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_run_properties: Optional[int]
    last_error: Optional[str]
    total_properties_found: Optional[int]
    created_at: Optional[datetime]
    investigation_status: Optional[str]
    investigation_ran_at: Optional[datetime]
    investigation_data: Optional[str]

    class Config:
        from_attributes = True


# --- Helpers ---

def _record_probe(db, probe_id: str, domain: str, success: bool):
    """Upsert a success/fail count for a probe+domain pair in the library."""
    entry = db.query(ScraperStrategyLibrary).filter(
        ScraperStrategyLibrary.probe_id == probe_id,
        ScraperStrategyLibrary.domain == domain,
    ).first()
    if not entry:
        entry = ScraperStrategyLibrary(
            probe_id=probe_id, domain=domain,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db.add(entry)
    if success:
        entry.success_count = (entry.success_count or 0) + 1
        entry.last_success_at = datetime.utcnow()
    else:
        entry.fail_count = (entry.fail_count or 0) + 1
    entry.updated_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()


def _try_library_probes(source_url: str, session: requests.Session, db) -> Optional[dict]:
    """
    Try probes from PROBE_REGISTRY, ordered by global success rate.
    Skips probes that have failed this domain > 3 times with 0 successes.
    Returns a strategy dict (ready to store in investigation_data['strategy'])
    if a probe finds >= 3 property cards on the test page, else None.
    """
    domain = urlparse(source_url).netloc.lower()

    # Load library stats for this domain
    domain_entries = {
        e.probe_id: e for e in
        db.query(ScraperStrategyLibrary)
        .filter(ScraperStrategyLibrary.domain == domain).all()
    }
    global_entries = {
        e.probe_id: e for e in
        db.query(ScraperStrategyLibrary)
        .filter(ScraperStrategyLibrary.domain == None).all()
    }

    def probe_sort_key(probe_id):
        if probe_id in domain_entries and domain_entries[probe_id].success_count > 0:
            return (0, -domain_entries[probe_id].success_count)  # domain hit first
        if probe_id in global_entries and global_entries[probe_id].success_count > 0:
            return (1, -global_entries[probe_id].success_count)  # global hit second
        return (2, 0)  # untried last

    ordered = sorted(PROBE_REGISTRY.keys(), key=probe_sort_key)

    for probe_id in ordered:
        # Skip probes that have repeatedly failed this domain
        e = domain_entries.get(probe_id)
        if e and e.fail_count >= 3 and (e.success_count or 0) == 0:
            continue

        probe = PROBE_REGISTRY[probe_id]
        try:
            test_url = probe['test_url'](source_url)
            logger.debug("Library probe '%s' → %s", probe_id, test_url)
            soup = _scrape_page(test_url, session)
            if not soup:
                _record_probe(db, probe_id, domain, success=False)
                continue

            listings = _extract_listings(soup, test_url)
            if len(listings) >= 3:
                strategy = probe['strategy'](source_url)
                strategy['confirmed_by'] = f'library:{probe_id}'
                strategy['confirmed_at'] = datetime.utcnow().isoformat()
                strategy['probe_name'] = probe['name']
                _record_probe(db, probe_id, domain, success=True)
                logger.info("Library probe '%s' succeeded for %s (%d listings)", probe_id, domain, len(listings))
                return strategy
            else:
                _record_probe(db, probe_id, domain, success=False)

        except Exception as exc:
            logger.debug("Library probe '%s' error for %s: %s", probe_id, domain, exc)
            _record_probe(db, probe_id, domain, success=False)

    return None


def _derive_pagination_pattern(urls: List[str]) -> Optional[dict]:
    """
    Given 2+ sample page URLs, find the incrementing numeric path segment
    and return a pagination template dict, e.g.:
      { "template": "https://site.com/search/{page}/", "query": "submit=1", "start_page": 1 }
    Returns None if no clear pattern is found.
    """
    cleaned = [u.strip() for u in (urls or []) if u.strip()]
    if len(cleaned) < 2:
        return None

    parsed = [urlparse(u) for u in cleaned]

    # Split paths into non-empty segments
    def path_parts(p):
        return [s for s in p.path.strip('/').split('/') if s]

    parts_list = [path_parts(p) for p in parsed]

    # All must have same segment count
    if len(set(len(p) for p in parts_list)) != 1:
        return None

    n_segs = len(parts_list[0])
    varying_idx = None
    for i in range(n_segs):
        vals = [p[i] for p in parts_list]
        if all(v.isdigit() for v in vals) and len(set(vals)) == len(vals):
            # Check values are consecutive / sequential
            nums = sorted(int(v) for v in vals)
            diffs = [nums[j+1] - nums[j] for j in range(len(nums)-1)]
            if len(set(diffs)) == 1:  # consistent step
                varying_idx = i
                break

    if varying_idx is None:
        return None

    # Build template path — preserve trailing slash style from original URLs
    template_parts = list(parts_list[0])
    template_parts[varying_idx] = '{page}'
    base = f"{parsed[0].scheme}://{parsed[0].netloc}"
    has_trailing_slash = parsed[0].path.endswith('/')
    template_path = '/' + '/'.join(template_parts) + ('/' if has_trailing_slash else '')

    # Carry query string from the sample URLs
    query = parsed[0].query or ''

    # Infer start page from samples
    nums = sorted(int(p[varying_idx]) for p in parts_list)
    step = nums[1] - nums[0]
    start_page = 1 if nums[0] >= 2 else nums[0]

    template_url = base + template_path
    if query:
        template_url += '?' + query

    return {
        'template': template_url,
        'start_page': start_page,
        'step': step,
        'sample_pages': nums,
    }


def _robots_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(HEADERS['User-Agent'], url)
    except Exception:
        return True  # assume allowed if robots.txt unreachable


def _parse_price(text: str) -> Optional[int]:
    """Parse a price string into an integer number of pence (pounds actually).

    Handles:
    - Ranges: "£100,000-£150,000"  → 100000  (take lower bound)
    - Guide:  "£110,000+"          → 110000
    - Millions: "£2.5m" / "2.5M"  → 2500000
    - Thousands: "£150k"           → 150000
    - Plain:  "£110,000"           → 110000
    """
    if not text:
        return None
    text = text.strip()

    # £X.Xm / £Xm notation (millions)
    m = re.search(r'£?\s*([\d,]+\.?\d*)\s*[mM]\b', text)
    if m:
        try:
            return int(float(m.group(1).replace(',', '')) * 1_000_000)
        except (ValueError, TypeError):
            pass

    # £X.Xk / £Xk notation (thousands)
    m = re.search(r'£?\s*([\d,]+\.?\d*)\s*[kK]\b', text)
    if m:
        try:
            return int(float(m.group(1).replace(',', '')) * 1_000)
        except (ValueError, TypeError):
            pass

    # Take the FIRST £X,XXX number (handles ranges, guide +, etc.)
    m = re.search(r'£?\s*([\d]{1,3}(?:,[\d]{3})*)', text)
    if m:
        cleaned = m.group(1).replace(',', '')
        return int(cleaned) if cleaned else None

    # Last resort: strip everything non-digit
    cleaned = re.sub(r'[^\d]', '', text)
    return int(cleaned) if cleaned else None


def _extract_postcode(text: str) -> str:
    match = re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', text, re.IGNORECASE)
    return match.group(0).upper().strip() if match else ''


def _scrape_page(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        time.sleep(RATE_LIMIT)
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _extract_acuitus(soup: BeautifulSoup, base_url: str) -> list:
    """Site-specific extractor for acuitus.co.uk."""
    listings = []
    for card in soup.select('li.auction'):
        try:
            addr_el = card.select_one('.proplist-grid-address')
            if not addr_el:
                continue
            address = ' '.join(addr_el.get_text(separator=' ', strip=True).split())

            # Price: find 'Guide' dt then its following dd
            price = None
            status_dl = card.select_one('.proplist-grid-status')
            if status_dl:
                for dt in status_dl.find_all('dt'):
                    if 'Guide' in dt.get_text():
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            price = _parse_price(dd.get_text())
                        break

            lot_el = card.select_one('.lotnumber')
            lot = lot_el.get_text(strip=True) if lot_el else ''

            link_el = card.select_one('a[href]')
            source_url = urljoin(base_url, link_el['href']) if link_el else base_url

            listings.append({
                'address': address,
                'postcode': _extract_postcode(address),
                'guide_price': price,
                'lot_number': lot,
                'source_url': source_url,
            })
        except Exception:
            continue
    return listings


def _extract_agents_property_auction(soup: BeautifulSoup, base_url: str) -> list:
    """Site-specific extractor for agentspropertyauction.com."""
    listings = []
    for card in soup.select('.card--property'):
        try:
            addr_el = card.select_one('.card-title--property, .card-title, h3, h4')
            if not addr_el:
                continue
            address = addr_el.get_text(strip=True)
            if len(address) < 5:
                continue

            price_el = card.select_one('.card-price, [class*="price"]')
            price = _parse_price(price_el.get_text() if price_el else '')

            link_el = card.select_one('a[href]')
            source_url = urljoin(base_url, link_el['href']) if link_el else base_url

            listings.append({
                'address': address,
                'postcode': _extract_postcode(address),
                'guide_price': price,
                'lot_number': '',
                'source_url': source_url,
            })
        except Exception:
            continue
    return listings


def _fetch_wp_alm_pages(first_soup: BeautifulSoup, base_url: str,
                         session: requests.Session, extra_pages: int) -> list:
    """Fetch additional pages via the WordPress Ajax Load More plugin.

    Called after the first page has already been scraped. Sends POST requests
    to /wp-admin/admin-ajax.php with action=alm_get_posts, incrementing the
    page counter until the site signals no more results or we hit extra_pages.
    """
    parsed = urlparse(base_url)
    ajax_url = f"{parsed.scheme}://{parsed.netloc}/wp-admin/admin-ajax.php"

    # Pull the WP nonce from any inline script
    nonce = None
    for script in first_soup.find_all('script'):
        text = script.string or ''
        m = re.search(r'"nonce"\s*:\s*"([a-f0-9]+)"', text)
        if m:
            nonce = m.group(1)
            break

    if not nonce:
        logger.info("ALM: no nonce found for %s — skipping AJAX pagination", base_url)
        return []

    # Read button data-attributes for query parameters
    btn = first_soup.select_one(
        '.alm-load-more-btn, [data-repeater], button[data-post-type]'
    )
    posts_per_page = int(btn.get('data-posts-per-page', 9)) if btn else 9
    post_type = (btn.get('data-post-type') or 'post') if btn else 'post'
    repeater = (btn.get('data-repeater') or 'default') if btn else 'default'

    all_listings = []
    for page in range(1, extra_pages + 1):
        try:
            time.sleep(RATE_LIMIT)
            resp = session.post(ajax_url, data={
                'action': 'alm_get_posts',
                'nonce': nonce,
                'post_type': post_type,
                'posts_per_page': str(posts_per_page),
                'page': str(page),
                'offset': str(page * posts_per_page),
                'repeater': repeater,
                'canonical_url': base_url,
                'url': base_url,
            }, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            html = (data.get('html') or '').strip()
            if not html:
                logger.info("ALM: empty html on page %d, stopping", page)
                break
            page_soup = BeautifulSoup(html, 'html.parser')
            listings = _extract_agents_property_auction(page_soup, base_url)
            if not listings:
                break
            all_listings.extend(listings)
            logger.info("ALM page %d: %d listings", page, len(listings))
            # ALM sets 'remain' false (boolean or string) when exhausted
            remain = data.get('remain', True)
            if remain is False or remain == 'false' or remain == 0:
                break
        except Exception as e:
            logger.warning("ALM AJAX page %d failed: %s", page, e)
            break

    return all_listings


def _scrape_detail_acuitus(url: str, session: requests.Session) -> dict:
    """Fetch an Acuitus lot detail page and return extra fields."""
    extra = {}
    try:
        soup = _scrape_page(url, session)
        if not soup:
            return extra
        # Tenure
        tenure_el = soup.select_one('[class*="tenure"], .lot-details dt:-soup-contains("Tenure") + dd')
        if tenure_el:
            extra['tenure'] = tenure_el.get_text(strip=True)[:50]
        # Description
        desc_el = soup.select_one('.lot-description, .property-description, article .content')
        if desc_el:
            extra['description'] = desc_el.get_text(separator=' ', strip=True)[:2000]
        # Auction date (more precise)
        date_el = soup.select_one('[class*="auction-date"] time, time[datetime]')
        if date_el:
            extra['auction_date_text'] = date_el.get('datetime') or date_el.get_text(strip=True)
        # Legal pack
        legal_el = soup.select_one('a[href*="legal"], a[href*="pack"]')
        if legal_el:
            extra['legal_pack_url'] = urljoin(url, legal_el['href'])[:1000]
    except Exception as e:
        logger.debug("Acuitus detail page %s: %s", url, e)
    return extra


def _scrape_detail_apa(url: str, session: requests.Session) -> dict:
    """Fetch an agentspropertyauction.com detail page and return extra fields."""
    extra = {}
    try:
        soup = _scrape_page(url, session)
        if not soup:
            return extra
        # Description — look for the main content block
        desc_el = soup.select_one(
            '.property-description, .entry-content, .property-details-description, article .content'
        )
        if desc_el:
            extra['description'] = desc_el.get_text(separator=' ', strip=True)[:2000]
        # Guide price (may be more detailed on the detail page)
        price_el = soup.select_one('[class*="guide-price"], [class*="price"]')
        if price_el:
            p = _parse_price(price_el.get_text())
            if p:
                extra['guide_price'] = p
        # Tenure
        for label_el in soup.select('th, dt, label, strong'):
            label_text = label_el.get_text(strip=True).lower()
            if 'tenure' in label_text:
                value_el = label_el.find_next_sibling() or label_el.find_next('td') or label_el.find_next('dd')
                if value_el:
                    extra['tenure'] = value_el.get_text(strip=True)[:50]
                    break
        # Legal pack link
        legal_el = soup.select_one('a[href*="legal"], a[href*="pack"], a:-soup-contains("Legal Pack")')
        if legal_el:
            extra['legal_pack_url'] = urljoin(url, legal_el['href'])[:1000]
        # Lot reference
        ref_el = soup.select_one('[class*="lot-ref"], [class*="reference"], [class*="lot-num"]')
        if ref_el:
            extra['lot_number'] = ref_el.get_text(strip=True)[:50]
    except Exception as e:
        logger.debug("APA detail page %s: %s", url, e)
    return extra


# Map domain fragments to detail page scrapers
DETAIL_SCRAPERS = {
    'acuitus.co.uk': _scrape_detail_acuitus,
    'agentspropertyauction.com': _scrape_detail_apa,
}


def _scrape_allsop_json(source_url: str, session: requests.Session, max_pages: int) -> list:
    """Fetch all Allsop lots via their internal JSON search API.

    The Allsop platform is a React SPA. Properties are served from
    /api/search?auction_id=...&available_only=true&page=N&size=N
    which returns JSON with full lot detail — no HTML scraping needed.
    """
    parsed = urlparse(source_url)
    params_qs = dict(p.split('=', 1) for p in parsed.query.split('&') if '=' in p)
    auction_id = params_qs.get('auction_id')
    if not auction_id:
        logger.warning("Allsop: no auction_id in URL %s", source_url)
        return []

    api_base = f"{parsed.scheme}://{parsed.netloc}/api/search"
    page_size = 100  # fetch in batches of 100

    all_listings = []
    page = 1
    while page <= max_pages:
        try:
            time.sleep(RATE_LIMIT)
            resp = session.get(api_base, params={
                'auction_id': auction_id,
                'available_only': 'true',
                'page': page,
                'size': page_size,
            }, headers={**HEADERS, 'Accept': 'application/json'}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get('data', {}).get('results', [])
            if not results:
                break

            for lot in results:
                address = (
                    lot.get('full_address') or
                    lot.get('allsop_address') or
                    ', '.join(filter(None, [
                        lot.get('address1'), lot.get('address2'),
                        lot.get('town'), lot.get('county'), lot.get('postcode')
                    ]))
                )
                if not address or len(address) < 5:
                    continue

                guide = lot.get('guide_price_lower') or lot.get('website_price_lower')
                # Note: sort_price is a sort key, not a real price — do not use as fallback
                guide_price = int(guide) if guide and int(guide) >= 1000 else None

                postcode = (lot.get('postcode') or _extract_postcode(address) or '')[:10].strip()
                lot_number = str(lot.get('lot_number_text') or lot.get('lot_number') or '')
                lot_id = lot.get('allsop_lotid', '')
                detail_url = (
                    f"{parsed.scheme}://{parsed.netloc}/lot-overview?lotId={lot_id}"
                    if lot_id else source_url
                )

                all_listings.append({
                    'address': address,
                    'postcode': postcode,
                    'guide_price': guide_price,
                    'lot_number': lot_number[:50],
                    'source_url': detail_url[:500],
                    'description': lot.get('property_byline') or lot.get('allsop_propertybyline') or '',
                    'tenure': (lot.get('property_tenure') or lot.get('allsop_propertytenure') or '')[:50],
                    'auction_reference': (lot.get('reference') or lot.get('allsop_name') or '')[:100],
                })

            total = data.get('data', {}).get('total', 0)
            logger.info("Allsop JSON page %d: %d lots (total=%d)", page, len(results), total)
            if len(all_listings) >= total:
                break
            page += 1
        except Exception as e:
            logger.warning("Allsop JSON page %d failed: %s", page, e)
            break

    return all_listings


def _scrape_apa(source_url: str, session: requests.Session, max_pages: int) -> list:
    """Scrape agentspropertyauction.com using the ur_load_more WordPress AJAX plugin.

    The site uses a 'Load More' button that POSTs to /wp-admin/admin-ajax.php.
    The session cookie from the initial page load is required — requests.Session
    handles this automatically.
    """
    parsed = urlparse(source_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    ajax_url = f"{base}/wp-admin/admin-ajax.php"
    search_url = f"{base}/property-search/?submit=1"

    # Initial page load — stores session cookies
    time.sleep(RATE_LIMIT)
    try:
        resp = session.get(search_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("APA initial page failed: %s", e)
        return []

    first_soup = BeautifulSoup(resp.text, 'html.parser')
    all_listings = _extract_agents_property_auction(first_soup, base)
    logger.info("APA page 1: %d listings", len(all_listings))

    # Read pagination meta from the load-more button
    btn = first_soup.select_one('.ur-load-more-link')
    if not btn:
        logger.info("APA: no load-more button found, returning page 1 only")
        return all_listings

    max_page = int(btn.get('data-max', 1))
    pages_to_fetch = min(max_page, max_pages)
    logger.info("APA: %d total pages, fetching up to %d", max_page, pages_to_fetch)

    for page_num in range(2, pages_to_fetch + 1):
        try:
            time.sleep(RATE_LIMIT)
            resp = session.post(ajax_url, data={
                'action': 'ur_load_more',
                'page_number': str(page_num),
                'page_type': 'page',
            }, headers={
                **HEADERS,
                'Referer': search_url,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
            }, timeout=30)
            resp.raise_for_status()
            page_soup = BeautifulSoup(resp.text, 'html.parser')
            listings = _extract_agents_property_auction(page_soup, base)
            if not listings:
                logger.info("APA AJAX page %d: no listings, stopping", page_num)
                break
            all_listings.extend(listings)
            logger.info("APA AJAX page %d: %d listings", page_num, len(listings))
        except Exception as e:
            logger.warning("APA AJAX page %d failed: %s", page_num, e)
            break

    return all_listings


# Map domain fragments to site-specific extractors
SITE_HANDLERS = {
    'acuitus.co.uk': _extract_acuitus,
    'agentspropertyauction.com': _extract_agents_property_auction,
}

# Sites with JSON APIs — bypasses HTML scraping entirely
JSON_HANDLERS = {
    'allsop.co.uk': _scrape_allsop_json,
    'agentspropertyauction.com': _scrape_apa,
}


def _extract_listings(soup: BeautifulSoup, base_url: str) -> list:
    """Dispatch to site-specific extractor or fall back to generic."""
    domain = urlparse(base_url).netloc.lower()
    for pattern, handler in SITE_HANDLERS.items():
        if pattern in domain:
            return handler(soup, base_url)

    # Generic fallback
    listings = []
    card_selectors = [
        '.lot', '.property-lot', '.auction-lot', '[data-lot]',
        '.property-card', '.listing-card', '.property-item',
        'article.property', '.search-result', '.listing',
        '[class*="lot-"]', '[class*="property-"]', '[class*="listing-"]',
    ]
    cards = []
    for sel in card_selectors:
        found = soup.select(sel)
        if len(found) > 2:
            cards = found
            break

    if not cards:
        for tag in soup.find_all(['article', 'li']):
            text = tag.get_text()
            if re.search(r'£[\d,]+', text) and len(text) > 30:
                cards.append(tag)

    for card in cards[:50]:
        try:
            addr_el = card.select_one(
                '.address, .property-address, .lot-address, h2, h3, [class*="address"]'
            )
            if not addr_el:
                continue
            address = addr_el.get_text(strip=True)
            if len(address) < 5:
                continue

            price_el = card.select_one(
                '.guide-price, .price, .asking-price, [class*="price"], [data-price]'
            )
            price = _parse_price(price_el.get_text() if price_el else '')

            link_el = card.select_one('a[href]')
            source_url = urljoin(base_url, link_el['href']) if link_el else base_url

            lot_el = card.select_one('.lot-number, [class*="lot-num"], [data-lot]')
            lot_number = lot_el.get_text(strip=True) if lot_el else ''

            date_el = card.select_one('.auction-date, time, [class*="date"], [datetime]')
            date_text = date_el.get('datetime') or date_el.get_text(strip=True) if date_el else ''

            listings.append({
                'address': address,
                'postcode': _extract_postcode(address),
                'guide_price': price,
                'lot_number': lot_number,
                'source_url': source_url,
            })
        except Exception:
            continue

    return listings


def _find_next_page(soup: BeautifulSoup, current_url: str, page_num: int) -> Optional[str]:
    """Try to find a next page URL."""
    next_el = soup.select_one(
        'a[rel="next"], .pagination .next a, a.next, [aria-label="Next"], '
        'a.ur-load-more-link, a[class*="load-more-link"], a[class*="load-more"]:not(button)'
    )
    if next_el and next_el.get('href'):
        return urljoin(current_url, next_el['href'])
    # Try appending ?page=N or /page/N
    parsed = urlparse(current_url)
    if 'page=' in parsed.query:
        return re.sub(r'page=\d+', f'page={page_num}', current_url)
    if re.search(r'/page/\d+', parsed.path):
        return re.sub(r'/page/\d+', f'/page/{page_num}', current_url)
    # Append page param
    sep = '&' if parsed.query else '?'
    return f"{current_url}{sep}page={page_num}" if page_num > 1 else None


def _investigate_site(source_id: int):
    """Background task: analyse a source URL to determine pagination strategy and property detail depth."""
    from backend.models.base import SessionLocal
    db = SessionLocal()
    try:
        source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
        if not source:
            return

        source.investigation_status = 'running'
        source.investigation_ran_at = datetime.utcnow()
        db.commit()

        findings = {
            'url': source.url,
            'analysed_at': datetime.utcnow().isoformat(),
            'robots_allowed': True,
            'pagination': {},
            'property_cards': {},
            'detail_page': {},
            'ajax_indicators': [],
            'recommendations': [],
        }

        if not _robots_allowed(source.url):
            findings['robots_allowed'] = False
            findings['recommendations'].append('Blocked by robots.txt — cannot scrape this site.')
            source.investigation_status = 'done'
            source.investigation_data = json.dumps(findings)
            db.commit()
            return

        session = requests.Session()
        soup = _scrape_page(source.url, session)
        if not soup:
            findings['recommendations'].append('Could not fetch the page — check URL is accessible.')
            source.investigation_status = 'error'
            source.investigation_data = json.dumps(findings)
            db.commit()
            return

        # --- Detect property cards ---
        card_selectors = [
            ('li.auction', 'Acuitus auction list items'),
            ('.card--property', 'Property cards'),
            ('.lot', 'Lot items'),
            ('.property-card', 'Property cards'),
            ('.listing-card', 'Listing cards'),
            ('.property-item', 'Property items'),
            ('article.property', 'Property articles'),
            ('.search-result', 'Search results'),
            ('[class*="lot-"]', 'Lot-prefixed elements'),
            ('[class*="property-"]', 'Property-prefixed elements'),
        ]
        card_count = 0
        matched_selector = None
        for sel, label in card_selectors:
            found = soup.select(sel)
            if len(found) > 2:
                card_count = len(found)
                matched_selector = sel
                findings['property_cards'] = {
                    'selector': sel,
                    'label': label,
                    'count': card_count,
                }
                break

        if not card_count:
            # fallback: count elements with price patterns
            price_els = [el for el in soup.find_all(['article', 'li', 'div'])
                         if re.search(r'£[\d,]+', el.get_text()) and len(el.get_text()) > 30]
            card_count = len(price_els[:50])
            findings['property_cards'] = {
                'selector': 'fallback (£ price detection)',
                'count': card_count,
            }

        # --- Check for detail links ---
        detail_url = None
        if matched_selector:
            sample_card = soup.select(matched_selector)[0]
            link = sample_card.select_one('a[href]')
            if link and link.get('href'):
                href = link['href']
                if href.startswith('http') or href.startswith('/'):
                    detail_url = urljoin(source.url, href)
                    findings['detail_page']['sample_url'] = detail_url

        # --- Probe a detail page ---
        if detail_url and detail_url != source.url:
            detail_soup = _scrape_page(detail_url, session)
            if detail_soup:
                detail_fields = []
                field_patterns = {
                    'price': ['.guide-price', '[class*="price"]', '.price'],
                    'description': ['.description', '.property-description', 'article p'],
                    'bedrooms': ['[class*="bed"]', '[class*="bedroom"]'],
                    'epc': ['[class*="epc"]', '[class*="energy"]'],
                    'tenure': ['[class*="tenure"]'],
                    'auction_date': ['[class*="date"]', 'time'],
                    'legal_pack': ['[class*="legal"]', 'a[href*="legal"]'],
                }
                for field, selectors in field_patterns.items():
                    for sel in selectors:
                        if detail_soup.select(sel):
                            detail_fields.append(field)
                            break
                findings['detail_page']['extra_fields_available'] = detail_fields
                findings['detail_page']['has_detail_page'] = bool(detail_fields)
                if detail_fields:
                    findings['recommendations'].append(
                        f'Detail pages available with extra data: {", ".join(detail_fields)}. '
                        'Consider fetching individual property pages for richer data.'
                    )

        # --- Detect pagination ---
        next_el = soup.select_one('a[rel="next"], .pagination .next a, a.next, [aria-label="Next"]')
        page_nums = soup.select('.pagination a, [class*="page"] a')
        load_more = soup.select_one('button[class*="load"], a[class*="load-more"], [data-loadmore]')
        ajax_patterns = [
            ('data-page', 'AJAX pagination via data-page attribute'),
            ('data-ajax', 'AJAX content loading'),
            ('infinite-scroll', 'Infinite scroll detected'),
            ('loadmore', 'Load More button/AJAX'),
        ]

        ajax_found = []
        html_lower = str(soup)[:50000].lower()
        for pattern, desc in ajax_patterns:
            if pattern.lower() in html_lower:
                ajax_found.append(desc)

        findings['ajax_indicators'] = ajax_found

        if next_el:
            findings['pagination'] = {'type': 'standard_next', 'detected': True,
                                       'max_pages_recommended': 10}
            findings['recommendations'].append('Standard next-page pagination detected — multi-page scraping will work well.')
        elif len(page_nums) > 2:
            max_page = 1
            for a in page_nums:
                try:
                    max_page = max(max_page, int(a.get_text(strip=True)))
                except (ValueError, TypeError):
                    pass
            findings['pagination'] = {'type': 'numbered', 'detected': True,
                                       'max_page_found': max_page,
                                       'max_pages_recommended': min(max_page, 20)}
            findings['recommendations'].append(f'Numbered pagination detected (up to page {max_page}).')
        elif load_more or ajax_found:
            findings['pagination'] = {'type': 'ajax_load_more', 'detected': True,
                                       'max_pages_recommended': 1}
            findings['recommendations'].append(
                'AJAX/Load More pagination detected — standard scraping only captures the first page. '
                'Full data requires Playwright (headless browser) to click Load More.'
            )
        else:
            # Try page=2 to see if URL pagination works
            test_url = f"{source.url}{'&' if '?' in source.url else '?'}page=2"
            test_soup = _scrape_page(test_url, session)
            if test_soup:
                test_count = 0
                if matched_selector:
                    test_count = len(test_soup.select(matched_selector))
                if test_count > 0:
                    findings['pagination'] = {'type': 'query_param', 'param': 'page',
                                               'detected': True, 'max_pages_recommended': 10}
                    findings['recommendations'].append('Query-parameter pagination (?page=N) confirmed working.')
                else:
                    findings['pagination'] = {'type': 'single_page', 'detected': False,
                                               'max_pages_recommended': 1}
                    findings['recommendations'].append('No pagination detected — all listings appear on one page.')
            else:
                findings['pagination'] = {'type': 'unknown', 'detected': False,
                                           'max_pages_recommended': 1}

        # --- Try library probes when standard detection found few or no cards ---
        # (i.e. site may need ?size=500, different pagination param, etc.)
        existing_strategy = None
        try:
            existing_inv = json.loads(source.investigation_data or '{}')
            existing_strategy = existing_inv.get('strategy')
        except Exception:
            pass

        if not existing_strategy and card_count < 5:
            logger.info("Few cards found (%d) for %s — trying library probes", card_count, source.name)
            auto_strategy = _try_library_probes(source.url, session, db)
            if auto_strategy:
                findings['strategy'] = auto_strategy
                findings['recommendations'].insert(0,
                    f'Auto-configured via library probe "{auto_strategy.get("probe_name", "")}" — '
                    f'no manual hint needed.'
                )
                # Update card count summary to reflect probe success
                probe_type = auto_strategy.get('type', '')
                if probe_type == 'all_results_url':
                    findings['summary'] = f'Auto-configured: all-results URL via {auto_strategy.get("probe_name")}.'
                else:
                    tmpl = auto_strategy.get('pagination_template', {})
                    findings['summary'] = f'Auto-configured: pagination template via {auto_strategy.get("probe_name")}.'
            else:
                findings['recommendations'].append(
                    'Could not auto-configure — open the analysis panel and use "Help configure scraping" '
                    'to provide a sample page URL or an all-results URL.'
                )

        findings['summary'] = (
            f"Found {card_count} property cards on first page. "
            f"Pagination: {findings['pagination'].get('type', 'unknown')}. "
            f"Detail pages: {'yes' if findings['detail_page'].get('has_detail_page') else 'no extra data found'}."
        )

        source.investigation_status = 'done'
        source.investigation_data = json.dumps(findings)
        db.commit()
        logger.info("Investigation complete for %s: %s", source.name, findings['summary'])

    except Exception as e:
        logger.error("Investigation error for source %s: %s", source_id, e)
        try:
            source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
            if source:
                source.investigation_status = 'error'
                source.investigation_data = json.dumps({'error': str(e)[:500]})
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _run_scraper(source_id: int):
    """Background task: scrape a source URL and save properties."""
    from backend.models.base import SessionLocal
    db = SessionLocal()
    run_id = str(uuid.uuid4())
    try:
        source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
        if not source:
            return

        source.last_run_status = 'running'
        source.last_run_at = datetime.utcnow()
        source.last_run_id = run_id if hasattr(source, 'last_run_id') else None
        db.commit()

        _db_log(db, source_id, run_id, 'info', f'Scrape started for {source.name}')

        if not _robots_allowed(source.url):
            source.last_run_status = 'error'
            source.last_error = 'Blocked by robots.txt'
            db.commit()
            _db_log(db, source_id, run_id, 'error', 'Blocked by robots.txt')
            return

        session = requests.Session()
        all_listings = []
        domain = urlparse(source.url).netloc.lower()

        # Load stored strategy from investigation_data (user hints override auto-detection)
        inv_data = {}
        try:
            if source.investigation_data:
                inv_data = json.loads(source.investigation_data)
        except Exception:
            pass
        strategy = inv_data.get('strategy', {})

        # Check for JSON API handler first (bypasses HTML scraping entirely)
        json_handler = next((h for pat, h in JSON_HANDLERS.items() if pat in domain), None)

        if json_handler:
            all_listings = json_handler(source.url, session, source.max_pages)
            msg = f"Found {len(all_listings)} listings via API handler"
            logger.info("Source %s JSON handler: %d listings", source.name, len(all_listings))
            _db_log(db, source_id, run_id, 'info', msg)

        elif strategy.get('all_results_url'):
            # User provided a single URL that returns all results
            url = strategy['all_results_url']
            logger.info("Source %s using all-results URL: %s", source.name, url)
            soup = _scrape_page(url, session)
            if soup:
                all_listings = _extract_listings(soup, url)
                logger.info("Source %s all-results: %d listings", source.name, len(all_listings))

        elif strategy.get('pagination_template'):
            # User provided sample page URLs → derived template
            tmpl = strategy['pagination_template']
            template = tmpl['template']
            start = tmpl.get('start_page', 1)
            logger.info("Source %s using pagination template: %s (start=%d)", source.name, template, start)
            for page_num in range(start, start + source.max_pages):
                page_url = template.replace('{page}', str(page_num))
                soup = _scrape_page(page_url, session)
                if not soup:
                    break
                listings = _extract_listings(soup, page_url)
                if not listings:
                    break
                all_listings.extend(listings)
                logger.info("Source %s template page %d: %d listings", source.name, page_num, len(listings))

        else:
            # HTML scraping with standard pagination auto-detection
            first_soup = _scrape_page(source.url, session)
            if first_soup:
                first_page = _extract_listings(first_soup, source.url)
                all_listings.extend(first_page)
                logger.info("Source %s page 1: %d listings", source.name, len(first_page))

                url = source.url
                current_soup = first_soup
                for page_num in range(2, source.max_pages + 1):
                    next_url = _find_next_page(current_soup, url, page_num)
                    if not next_url or next_url == url:
                        break
                    current_soup = _scrape_page(next_url, session)
                    if not current_soup:
                        break
                    page_listings = _extract_listings(current_soup, source.url)
                    if not page_listings:
                        break
                    all_listings.extend(page_listings)
                    logger.info("Source %s page %d: %d listings", source.name, page_num, len(page_listings))
                    url = next_url

        # Optional detail page enrichment
        if source.scrape_detail_pages:
            detail_fn = None
            for pattern, fn in DETAIL_SCRAPERS.items():
                if pattern in domain:
                    detail_fn = fn
                    break
            if detail_fn:
                logger.info("Enriching %d listings with detail pages", len(all_listings))
                for listing in all_listings:
                    detail_url = listing.get('source_url')
                    if detail_url and detail_url != source.url:
                        extra = detail_fn(detail_url, session)
                        listing.update({k: v for k, v in extra.items() if v})

        # Save to database
        new_count = 0
        first_save_error = None
        for listing in all_listings:
            try:
                sp = db.begin_nested()
                existing = db.query(Property).filter(
                    Property.address == listing['address']
                ).first()

                if not existing:
                    prop = Property(
                        address=listing['address'],
                        postcode=(listing.get('postcode') or '')[:10].strip(),
                        property_type='unknown',
                        asking_price=listing.get('guide_price'),
                        status='active',
                        date_found=datetime.utcnow().date(),
                    )
                    db.add(prop)
                    db.flush()

                    if source.source_type == 'auction':
                        auction = Auction(
                            property_id=prop.id,
                            auctioneer=source.name[:100],
                            lot_number=(listing.get('lot_number') or '')[:50],
                            guide_price=listing.get('guide_price'),
                            auction_date=datetime.utcnow(),
                            auction_house_url=(listing.get('source_url') or '')[:500],
                            is_sold=False,
                            sale_status='upcoming',
                            description=listing.get('description') or None,
                            tenure=(listing.get('tenure') or '')[:50] or None,
                            legal_pack_url=(listing.get('legal_pack_url') or '')[:1000] or None,
                            auction_reference=(listing.get('auction_reference') or '')[:100] or None,
                        )
                        db.add(auction)
                    new_count += 1
                sp.commit()
            except Exception as e:
                sp.rollback()
                err_msg = str(e)[:200]
                logger.warning("Error saving listing %s: %s", listing.get('address', '?'), err_msg)
                if first_save_error is None:
                    first_save_error = err_msg

        db.commit()

        source.last_run_status = 'success'
        source.last_run_properties = new_count
        source.total_properties_found = (source.total_properties_found or 0) + new_count
        source.last_error = first_save_error
        db.commit()
        msg = f"Scrape complete: {new_count} new properties saved (from {len(all_listings)} found)"
        logger.info("Scrape complete for %s: %d new properties", source.name, new_count)
        _db_log(db, source_id, run_id, 'info', msg)

        # Auto-score all active properties after each scrape
        try:
            _db_log(db, source_id, run_id, 'info', 'Running investment scoring…')
            scorer = PropertyScoringService(db)
            props = db.query(Property).filter(Property.status == 'active').all()
            for prop in props:
                try:
                    existing_score = db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()
                    result = scorer.score_property(prop, existing_score=existing_score)
                    save_score(db, prop, result)
                except Exception as se:
                    logger.debug("Scoring failed for property %d: %s", prop.id, se)
            db.commit()
            logger.info("Auto-scoring complete: %d properties scored", len(props))
            _db_log(db, source_id, run_id, 'info', f'Scoring complete: {len(props)} properties scored')
        except Exception as se:
            logger.warning("Auto-scoring failed: %s", se)
            _db_log(db, source_id, run_id, 'warning', f'Scoring failed: {se}')

    except Exception as e:
        logger.error("Scraper error for source %s: %s", source_id, e)
        _db_log(db, source_id, run_id, 'error', f'Scraper error: {e}')
        try:
            source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
            if source:
                source.last_run_status = 'error'
                source.last_error = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# --- Endpoints ---

@router.get('', response_model=List[ScraperSourceResponse])
def list_sources(db: Session = Depends(get_db)):
    return db.query(ScraperSource).order_by(ScraperSource.created_at.desc()).all()


@router.post('', response_model=ScraperSourceResponse)
def add_source(payload: ScraperSourceCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    source = ScraperSource(**payload.model_dump())
    source.investigation_status = 'pending'
    db.add(source)
    db.commit()
    db.refresh(source)
    background_tasks.add_task(_investigate_site, source.id)
    return source


@router.delete('/{source_id}')
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"message": "Deleted"}


@router.patch('/{source_id}', response_model=ScraperSourceResponse)
def update_source(source_id: int, payload: ScraperSourceUpdate, db: Session = Depends(get_db)):
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.patch('/{source_id}/toggle', response_model=ScraperSourceResponse)
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.is_active = not source.is_active
    db.commit()
    db.refresh(source)
    return source


@router.post('/{source_id}/run')
def run_source(source_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.last_run_status == 'running':
        raise HTTPException(status_code=409, detail="Scraper already running")
    background_tasks.add_task(_run_scraper, source_id)
    return {"message": f"Scraper started for {source.name}"}


@router.post('/{source_id}/investigate')
def investigate_source(source_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.investigation_status == 'running':
        raise HTTPException(status_code=409, detail="Investigation already running")
    source.investigation_status = 'pending'
    db.commit()
    background_tasks.add_task(_investigate_site, source_id)
    return {"message": f"Investigation started for {source.name}"}


@router.post('/{source_id}/hint', response_model=ScraperSourceResponse)
def save_hint(source_id: int, hint: ScraperHint, db: Session = Depends(get_db)):
    """
    Save a user-provided scraping hint:
    - all_results_url: a URL that returns all results on one page
    - page_urls: 2+ sample page URLs to derive a pagination template
    The derived strategy is merged into investigation_data.strategy.
    """
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Load existing investigation data
    inv_data = {}
    try:
        if source.investigation_data:
            inv_data = json.loads(source.investigation_data)
    except Exception:
        pass

    strategy = {}

    if hint.all_results_url and hint.all_results_url.strip():
        strategy = {
            'type': 'all_results_url',
            'all_results_url': hint.all_results_url.strip(),
            'confirmed_by': 'user_hint',
            'confirmed_at': datetime.utcnow().isoformat(),
        }

    elif hint.page_urls and len(hint.page_urls) >= 2:
        tmpl = _derive_pagination_pattern(hint.page_urls)
        if not tmpl:
            raise HTTPException(
                status_code=422,
                detail="Could not derive a pagination pattern from those URLs. "
                       "Make sure they differ only by an incrementing page number."
            )
        strategy = {
            'type': 'pagination_template',
            'pagination_template': tmpl,
            'confirmed_by': 'user_hint',
            'confirmed_at': datetime.utcnow().isoformat(),
        }

    else:
        raise HTTPException(status_code=422, detail="Provide either all_results_url or at least 2 page_urls")

    inv_data['strategy'] = strategy
    source.investigation_data = json.dumps(inv_data)
    db.commit()

    # Record this as a success in the library so future sites benefit
    domain = urlparse(source.url).netloc.lower()
    probe_id = _match_strategy_to_probe(strategy, source.url)
    if probe_id:
        _record_probe(db, probe_id, domain, success=True)
        _record_probe(db, probe_id, None, success=True)  # global count too

    db.refresh(source)
    return source


def _match_strategy_to_probe(strategy: dict, source_url: str) -> Optional[str]:
    """Try to match a user-provided strategy back to a known probe_id."""
    if not strategy:
        return None
    stype = strategy.get('type')
    if stype == 'all_results_url':
        url = strategy.get('all_results_url', '')
        if 'size=500' in url:
            return 'allresults_size_500'
        if 'per_page=500' in url:
            return 'allresults_per_page_500'
        if 'limit=500' in url:
            return 'allresults_limit_500'
        if 'count=500' in url:
            return 'allresults_count_500'
    if stype == 'pagination_template':
        tmpl = strategy.get('pagination_template', {}).get('template', '')
        if '/page/{page}/' in tmpl:
            return 'wp_page_path'
        if '/{page}/' in tmpl and tmpl.count('/') > 4:
            return 'numbered_path'
        if 'page={page}' in tmpl:
            return 'query_page'
        if 'paged={page}' in tmpl:
            return 'query_paged'
        if 'offset={page}' in tmpl:
            return 'query_offset_20'
    return None


@router.get('/library')
def get_library(db: Session = Depends(get_db)):
    """Return the strategy library — all known probes with their success/fail stats."""
    entries = db.query(ScraperStrategyLibrary).order_by(
        ScraperStrategyLibrary.success_count.desc()
    ).all()

    # Group by probe_id, aggregating across domains
    from collections import defaultdict
    by_probe = defaultdict(lambda: {'success_count': 0, 'fail_count': 0, 'domains': []})
    for e in entries:
        by_probe[e.probe_id]['success_count'] += e.success_count or 0
        by_probe[e.probe_id]['fail_count'] += e.fail_count or 0
        if e.domain:
            by_probe[e.probe_id]['domains'].append(e.domain)

    result = []
    for probe_id, probe in PROBE_REGISTRY.items():
        stats = by_probe.get(probe_id, {'success_count': 0, 'fail_count': 0, 'domains': []})
        result.append({
            'probe_id': probe_id,
            'name': probe['name'],
            'description': probe['description'],
            'type': probe['type'],
            'success_count': stats['success_count'],
            'fail_count': stats['fail_count'],
            'domains': stats['domains'][:5],  # cap for display
        })

    # Sort: most successful first, then alphabetical
    result.sort(key=lambda x: (-x['success_count'], x['name']))
    return result


@router.get('/{source_id}/logs')
def get_run_logs(source_id: int, run_id: Optional[str] = None, limit: int = 200, db: Session = Depends(get_db)):
    """Return recent log entries for a source. Optionally filter to a specific run_id."""
    q = db.query(ScraperRunLog).filter(ScraperRunLog.source_id == source_id)
    if run_id:
        q = q.filter(ScraperRunLog.run_id == run_id)
    logs = q.order_by(ScraperRunLog.created_at.desc()).limit(limit).all()
    return [
        {
            'id': l.id,
            'run_id': l.run_id,
            'run_type': l.run_type,
            'level': l.level,
            'message': l.message,
            'created_at': l.created_at.isoformat(),
        }
        for l in reversed(logs)  # return chronological order
    ]


@router.get('/{source_id}/latest-run-id')
def get_latest_run_id(source_id: int, db: Session = Depends(get_db)):
    """Return the run_id of the most recent log entry for this source."""
    latest = (
        db.query(ScraperRunLog)
        .filter(ScraperRunLog.source_id == source_id)
        .order_by(ScraperRunLog.created_at.desc())
        .first()
    )
    return {'run_id': latest.run_id if latest else None}
