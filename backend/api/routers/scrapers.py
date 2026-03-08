"""Scraper source management endpoints."""
import json
import logging
import re
import time
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
from backend.models.property import Property
from backend.models.auction import Auction
from backend.models.scraper_source import ScraperSource

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/scrapers', tags=['scrapers'])

HEADERS = {
    'User-Agent': 'AssetLens/1.0 (property investment research; contact@assetlens.co.uk)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
}
RATE_LIMIT = 2.0


# --- Schemas ---

class ScraperSourceCreate(BaseModel):
    name: str
    url: str
    source_type: str = 'auction'
    max_pages: int = 5
    notes: Optional[str] = None


class ScraperSourceResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: str
    is_active: bool
    max_pages: int
    notes: Optional[str]
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
    if not text:
        return None
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


# Map domain fragments to site-specific extractors
SITE_HANDLERS = {
    'acuitus.co.uk': _extract_acuitus,
    'agentspropertyauction.com': _extract_agents_property_auction,
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
    next_el = soup.select_one('a[rel="next"], .pagination .next a, a.next, [aria-label="Next"]')
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
    try:
        source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
        if not source:
            return

        source.last_run_status = 'running'
        source.last_run_at = datetime.utcnow()
        db.commit()

        if not _robots_allowed(source.url):
            source.last_run_status = 'error'
            source.last_error = 'Blocked by robots.txt'
            db.commit()
            return

        session = requests.Session()
        all_listings = []
        url = source.url

        for page_num in range(1, source.max_pages + 1):
            soup = _scrape_page(url, session)
            if not soup:
                break
            page_listings = _extract_listings(soup, source.url)
            if not page_listings:
                break
            all_listings.extend(page_listings)
            logger.info("Source %s page %d: %d listings", source.name, page_num, len(page_listings))

            next_url = _find_next_page(soup, url, page_num + 1)
            if not next_url or next_url == url:
                break
            url = next_url

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
                        postcode=listing.get('postcode', '') or '',
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
        source.last_error = first_save_error  # None if all saved OK, else first error seen
        db.commit()
        logger.info("Scrape complete for %s: %d new properties", source.name, new_count)

    except Exception as e:
        logger.error("Scraper error for source %s: %s", source_id, e)
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
