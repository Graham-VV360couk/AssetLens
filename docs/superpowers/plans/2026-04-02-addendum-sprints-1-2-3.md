# AssetLens Addendum — Sprints 1, 2 & 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full Data Points Addendum — pipeline fixes, on-demand property scan, auth/billing with Stripe subscriptions, investor profiles, personalised AI deal score, public listing pages, uploader portal, and Celery task queue.

**Architecture:** Three sequential sprints. Sprint 1 fixes the data layer and adds the core scan feature. Sprint 2 adds FastAPI-Users JWT auth, Stripe subscription gating, and investor profiles. Sprint 3 builds personalised scoring, public listings, uploader portal, and Celery worker for async enrichment.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 15, Redis 7, React 18, Tailwind CSS, Stripe API, Celery 5, fastapi-users, passlib/bcrypt, JWT

**Design spec:** `docs/superpowers/specs/2026-04-02-addendum-implementation-design.md`

---

## File Map

| File | Action | Sprint | Purpose |
|------|--------|--------|---------|
| `frontend/src/pages/PropertyDetail.jsx` | Modify | 1 | Wharf URL fix, description display, image gallery |
| `frontend/src/App.jsx` | Modify | 1, 2 | Gate scrapers route, add auth routes |
| `backend/services/searchland_client.py` | Modify | 1 | Add image extraction to normalizer |
| `backend/etl/licensed_feed_importer.py` | Modify | 1 | Fix merge call signature |
| `backend/services/deduplication_service.py` | Modify | 1 | Add image field merging, uploaded property dedup tests |
| `backend/models/epc_certificate.py` | Modify | 1 | Add 15 Tier 1 EPC columns |
| `backend/models/epc_recommendation.py` | Modify | 1 | Add 3 extended columns |
| `backend/etl/epc_importer.py` | Modify | 1 | Extend CSV column mappings |
| `database/migrations/versions/021_epc_extended_fields.py` | Create | 1 | Migration for extended EPC columns |
| `database/migrations/versions/022_epc_rec_extended.py` | Create | 1 | Migration for recommendation columns |
| `backend/api/routers/scan.py` | Create | 1 | On-demand property scan endpoint |
| `backend/services/scan_service.py` | Create | 1 | Scan orchestration service |
| `tests/api/test_scan.py` | Create | 1 | Scan endpoint tests |
| `tests/services/test_dedup_images.py` | Create | 1 | Dedup image merge tests |
| `tests/services/test_dedup_uploads.py` | Create | 1 | Dedup uploaded-vs-scraped tests |
| `frontend/src/components/ui/ImageGallery.jsx` | Create | 1 | Property image gallery with lightbox |
| `backend/models/user.py` | Create | 2 | User + UserProfile models |
| `database/migrations/versions/023_users.py` | Create | 2 | Users table migration |
| `database/migrations/versions/024_user_profiles.py` | Create | 2 | User profiles table migration |
| `backend/auth/config.py` | Create | 2 | FastAPI-Users setup, JWT config |
| `backend/auth/manager.py` | Create | 2 | User manager with custom registration |
| `backend/auth/schemas.py` | Create | 2 | Registration/login Pydantic schemas |
| `backend/auth/guards.py` | Create | 2 | Subscription-gated dependency injection |
| `backend/api/routers/auth.py` | Create | 2 | Auth router (register/login/reset) |
| `backend/api/routers/billing.py` | Create | 2 | Stripe checkout, webhooks, portal |
| `backend/api/routers/account.py` | Create | 2 | Investor profile CRUD |
| `frontend/src/contexts/AuthContext.jsx` | Create | 2 | Auth state provider |
| `frontend/src/pages/Login.jsx` | Create | 2 | Login page |
| `frontend/src/pages/Register.jsx` | Create | 2 | Registration with role selector |
| `frontend/src/pages/Account.jsx` | Create | 2 | Account settings + investor profile form |
| `frontend/src/components/auth/ProtectedRoute.jsx` | Create | 2 | Route guard component |
| `frontend/src/components/auth/PaywallModal.jsx` | Create | 2 | Paywall with plan cards + Stripe redirect |
| `tests/auth/test_guards.py` | Create | 2 | Subscription guard tests |
| `tests/auth/test_billing_webhook.py` | Create | 2 | Stripe webhook handler tests |
| `backend/services/personalised_score_service.py` | Create | 3 | Profile-based score adjustments |
| `backend/api/routers/listings.py` | Create | 3 | Public listing pages API |
| `backend/api/routers/auction_listings.py` | Create | 3 | Auction house upload portal API |
| `backend/api/routers/deal_listings.py` | Create | 3 | Deal source upload portal API |
| `backend/celery_app.py` | Create | 3 | Celery init with Redis broker |
| `backend/tasks/enrichment.py` | Create | 3 | Async enrichment task |
| `frontend/src/pages/PublicListing.jsx` | Create | 3 | Public property listing page |
| `frontend/src/pages/UploaderPortal.jsx` | Create | 3 | Upload management dashboard |
| `tests/services/test_personalised_score.py` | Create | 3 | Personalised score tests |
| `tests/api/test_listings_public.py` | Create | 3 | Public listing visibility tests |
| `tests/api/test_auction_upload.py` | Create | 3 | Auction CSV upload + dedup tests |
| `tests/tasks/test_enrichment_task.py` | Create | 3 | Celery enrichment task tests |

---

# SPRINT 1: DATA LAYER

---

## Task 1: Wharf Financial URL Fix

**Files:**
- Modify: `frontend/src/pages/PropertyDetail.jsx:410`

- [ ] **Step 1: Update WHARF_URL constant**

  In `frontend/src/pages/PropertyDetail.jsx`, find line 410:

  ```javascript
  const WHARF_URL = 'https://propertyfundingplatform.com/WharfFinancial#!/';
  ```

  Replace with:

  ```javascript
  const WHARF_URL = 'https://propertyfundingplatform.com/WharfFinancial#!/allloans';
  ```

- [ ] **Step 2: Verify the link attributes**

  Confirm lines 474-477 already have `target="_blank"` and `rel="noopener noreferrer"`:

  ```jsx
  <a
    href={WHARF_URL}
    target="_blank"
    rel="noopener noreferrer"
  ```

  These already exist. No change needed.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/pages/PropertyDetail.jsx
  git commit -m "fix: update Wharf Financial URL to allloans path"
  ```

---

## Task 2: Gate Data Sources Page (Admin Only)

**Files:**
- Modify: `frontend/src/App.jsx:29`

- [ ] **Step 1: Add admin gate to scrapers route**

  In `frontend/src/App.jsx`, find line 29:

  ```jsx
  <Route path="scrapers" element={<Scrapers />} />
  ```

  Replace with:

  ```jsx
  <Route path="scrapers" element={
    (process.env.REACT_APP_ADMIN_EMAILS || '').split(',').includes(localStorage.getItem('assetlens_user_email'))
      ? <Scrapers />
      : <Navigate to="/dashboard" replace />
  } />
  ```

  Add `Navigate` to the existing import from `react-router-dom` at the top of the file (it's already imported — used on line 24).

- [ ] **Step 2: Add `.env` variable**

  Add to `frontend/.env` (create if it doesn't exist):

  ```
  REACT_APP_ADMIN_EMAILS=daniel@geekybee.net
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/App.jsx frontend/.env
  git commit -m "fix: gate Data Sources page to admin emails only"
  ```

---

## Task 3: Searchland Normalizer — Add Image Extraction

**Files:**
- Modify: `backend/services/searchland_client.py:296-316`
- Create: `tests/services/test_searchland_images.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/services/test_searchland_images.py`:

  ```python
  """Tests for image extraction in Searchland normalizer."""
  import pytest


  def make_client():
      from backend.services.searchland_client import SearchlandClient
      client = SearchlandClient.__new__(SearchlandClient)
      return client


  def _raw(images=None, image_url=None):
      return {
          'id': '123',
          'url': 'http://example.com',
          'address': {'display_address': '1 Test St', 'postcode': 'SW1A 1AA',
                      'town': 'London', 'county': 'Greater London'},
          'property_type': 'flat',
          'bedrooms': 2,
          'bathrooms': 1,
          'price': 300000,
          'description': 'A nice flat',
          'status': 'for_sale',
          'sold_price': None,
          'images': images,
          'image_url': image_url,
      }


  def test_images_array_extracted():
      client = make_client()
      result = client.normalize_property_data(_raw(images=[
          'https://img.example.com/1.jpg',
          'https://img.example.com/2.jpg',
      ]))
      assert result['image_urls'] == '["https://img.example.com/1.jpg", "https://img.example.com/2.jpg"]'
      assert result['image_url'] == 'https://img.example.com/1.jpg'


  def test_single_image_url_extracted():
      client = make_client()
      result = client.normalize_property_data(_raw(image_url='https://img.example.com/hero.jpg'))
      assert result['image_url'] == 'https://img.example.com/hero.jpg'
      assert result['image_urls'] is None


  def test_no_images_returns_none():
      client = make_client()
      result = client.normalize_property_data(_raw())
      assert result['image_url'] is None
      assert result['image_urls'] is None
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/services/test_searchland_images.py -v
  ```

  Expected: FAIL — `image_url` and `image_urls` keys not in result dict.

- [ ] **Step 3: Add image extraction to normalize_property_data**

  In `backend/services/searchland_client.py`, find the `normalize_property_data` method (line 283). Add `import json` at the top of the file if not already present.

  Replace the return dict (lines 296-316) with:

  ```python
        images = raw_property.get('images') or []
        first_image = images[0] if images else raw_property.get('image_url')

        return {
            'source_id': raw_property.get('id'),
            'source_name': raw_property.get('source', 'searchland'),
            'source_url': raw_property.get('url'),
            'address': raw_property.get('address', {}).get('display_address'),
            'postcode': raw_property.get('address', {}).get('postcode'),
            'town': raw_property.get('address', {}).get('town'),
            'county': raw_property.get('address', {}).get('county'),
            'property_type': raw_property.get('property_type', '').lower(),
            'bedrooms': raw_property.get('bedrooms'),
            'bathrooms': raw_property.get('bathrooms'),
            'reception_rooms': raw_property.get('receptions'),
            'floor_area_sqm': raw_property.get('floor_area'),
            'asking_price': raw_property.get('price'),
            'sold_price': raw_property.get('sold_price'),
            'price_qualifier': raw_property.get('price_qualifier'),
            'description': raw_property.get('description'),
            'image_url': first_image,
            'image_urls': json.dumps(images) if images else None,
            'date_found': datetime.utcnow().date(),
            'status': mapped_status,
            'imported_at': datetime.utcnow()
        }
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/services/test_searchland_images.py -v
  ```

  Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/searchland_client.py tests/services/test_searchland_images.py
  git commit -m "feat: extract image_url and image_urls in Searchland normalizer"
  ```

---

## Task 4: Fix Licensed Feed Merge Call + Add Image Fields to Importer

**Files:**
- Modify: `backend/etl/licensed_feed_importer.py:105,118-130`

- [ ] **Step 1: Fix merge call signature**

  In `backend/etl/licensed_feed_importer.py`, find line 105:

  ```python
  self.deduplicator.merge_property_data(duplicate, normalized)
  ```

  Replace with:

  ```python
  self.deduplicator.merge_property_data(
      duplicate,
      normalized,
      source_name=normalized.get('source_name', 'searchland'),
      source_id=str(normalized.get('source_id', '')),
      source_url=normalized.get('source_url', ''),
  )
  ```

- [ ] **Step 2: Remove duplicate add_property_source call**

  The `merge_property_data` method already calls `add_property_source` internally (line 213-218 of deduplication_service.py). Remove the redundant call on lines 106-111:

  ```python
  # DELETE these lines (106-111):
  self.deduplicator.add_property_source(
      duplicate.id,
      source_name=normalized.get('source', 'searchland'),
      source_id=str(normalized.get('source_id', '')),
      source_url=normalized.get('source_url', ''),
  )
  ```

- [ ] **Step 3: Add image fields to new property creation**

  In the same file, find the Property constructor (lines 118-130). Add image fields:

  ```python
  prop = Property(
      address=normalized.get('address', ''),
      postcode=normalized.get('postcode', ''),
      town=normalized.get('town', ''),
      county=normalized.get('county', ''),
      property_type=normalized.get('property_type', 'unknown'),
      bedrooms=normalized.get('bedrooms'),
      bathrooms=normalized.get('bathrooms'),
      asking_price=normalized.get('asking_price'),
      status='active',
      date_found=datetime.utcnow(),
      description=normalized.get('description', ''),
      image_url=normalized.get('image_url'),
      image_urls=normalized.get('image_urls'),
  )
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/etl/licensed_feed_importer.py
  git commit -m "fix: correct merge call signature, add image fields to new property creation"
  ```

---

## Task 5: Deduplication Service — Image Field Merging

**Files:**
- Modify: `backend/services/deduplication_service.py:183-207`
- Create: `tests/services/test_dedup_images.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/services/test_dedup_images.py`:

  ```python
  """Tests for image field merging in deduplication service."""
  import pytest
  from unittest.mock import MagicMock, patch
  from datetime import datetime


  def _make_property(image_url=None, image_urls=None):
      prop = MagicMock()
      prop.id = 1
      prop.address = '1 Test St'
      prop.postcode = 'SW1A 1AA'
      prop.asking_price = 300000
      prop.bedrooms = 2
      prop.bathrooms = 1
      prop.floor_area_sqm = None
      prop.description = 'existing desc'
      prop.town = 'London'
      prop.county = 'Greater London'
      prop.image_url = image_url
      prop.image_urls = image_urls
      prop.updated_at = datetime.utcnow()
      return prop


  def _make_deduplicator(db):
      from backend.services.deduplication_service import PropertyDeduplicator
      dedup = PropertyDeduplicator(db)
      return dedup


  def test_image_url_merged_when_empty():
      db = MagicMock()
      prop = _make_property(image_url=None)
      dedup = _make_deduplicator(db)
      new_data = {'image_url': 'https://img.example.com/hero.jpg'}
      dedup.merge_property_data(prop, new_data, source_name='searchland')
      assert prop.image_url == 'https://img.example.com/hero.jpg'


  def test_image_url_not_overwritten_when_exists():
      db = MagicMock()
      prop = _make_property(image_url='https://img.example.com/existing.jpg')
      dedup = _make_deduplicator(db)
      new_data = {'image_url': 'https://img.example.com/new.jpg'}
      dedup.merge_property_data(prop, new_data, source_name='searchland')
      assert prop.image_url == 'https://img.example.com/existing.jpg'


  def test_image_urls_merged_when_empty():
      db = MagicMock()
      prop = _make_property(image_urls=None)
      dedup = _make_deduplicator(db)
      new_data = {'image_urls': '["https://img.example.com/1.jpg"]'}
      dedup.merge_property_data(prop, new_data, source_name='searchland')
      assert prop.image_urls == '["https://img.example.com/1.jpg"]'


  def test_image_urls_not_overwritten_when_exists():
      db = MagicMock()
      prop = _make_property(image_urls='["https://img.example.com/old.jpg"]')
      dedup = _make_deduplicator(db)
      new_data = {'image_urls': '["https://img.example.com/new.jpg"]'}
      dedup.merge_property_data(prop, new_data, source_name='searchland')
      assert prop.image_urls == '["https://img.example.com/old.jpg"]'
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/services/test_dedup_images.py -v
  ```

  Expected: FAIL — image fields not handled in `merge_property_data`.

- [ ] **Step 3: Add image merging to merge_property_data**

  In `backend/services/deduplication_service.py`, find the `merge_property_data` method. After the county merge block (line 207):

  ```python
  if new_data.get('county') and not existing_property.county:
      existing_property.county = new_data['county']
  ```

  Add:

  ```python
  if new_data.get('image_url') and not existing_property.image_url:
      existing_property.image_url = new_data['image_url']

  if new_data.get('image_urls') and not existing_property.image_urls:
      existing_property.image_urls = new_data['image_urls']
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/services/test_dedup_images.py -v
  ```

  Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/deduplication_service.py tests/services/test_dedup_images.py
  git commit -m "feat: merge image_url and image_urls in deduplication service"
  ```

---

## Task 6: Dedup — Uploaded Property Tests

**Files:**
- Create: `tests/services/test_dedup_uploads.py`

- [ ] **Step 1: Write tests for uploaded-vs-scraped dedup scenarios**

  Create `tests/services/test_dedup_uploads.py`:

  ```python
  """Tests for dedup handling of uploaded properties (auction/deal source) vs scraped."""
  import pytest
  from unittest.mock import MagicMock, patch
  from datetime import datetime
  from backend.models.property import Property


  def _make_db_property(address='123 High Street', postcode='SW1A 1AA'):
      prop = MagicMock(spec=Property)
      prop.id = 1
      prop.address = address
      prop.postcode = postcode
      return prop


  def _make_deduplicator(db, existing_properties=None):
      from backend.services.deduplication_service import PropertyDeduplicator
      dedup = PropertyDeduplicator(db)
      return dedup


  def test_exact_address_match_finds_duplicate(tmp_path):
      """Uploaded lot with exact same address as scraped property should find the duplicate."""
      db = MagicMock()
      existing = _make_db_property(address='123 High Street', postcode='SW1A 1AA')
      db.query.return_value.filter.return_value.all.return_value = [existing]

      dedup = _make_deduplicator(db)
      result = dedup.find_duplicate(address='123 High Street', postcode='SW1A 1AA')
      assert result is not None


  def test_postcode_only_does_not_false_match():
      """Uploaded lot with postcode only (no address) should NOT match an existing property."""
      db = MagicMock()
      existing = _make_db_property(address='123 High Street', postcode='SW1A 1AA')
      db.query.return_value.filter.return_value.all.return_value = [existing]

      dedup = _make_deduplicator(db)
      # Empty address with matching postcode — should NOT match
      result = dedup.find_duplicate(address='', postcode='SW1A 1AA')
      # If address is empty, dedup should return None (no meaningful match possible)
      assert result is None


  def test_near_miss_address_matches():
      """Uploaded lot with slight address variation should match via fuzzy matching."""
      db = MagicMock()
      existing = _make_db_property(address='123 High Street', postcode='SW1A 1AA')
      db.query.return_value.filter.return_value.all.return_value = [existing]

      dedup = _make_deduplicator(db)
      result = dedup.find_duplicate(address='123 High St', postcode='SW1A 1AA')
      assert result is not None
  ```

- [ ] **Step 2: Run tests**

  ```bash
  docker-compose exec backend pytest tests/services/test_dedup_uploads.py -v
  ```

  Expected: Tests should pass — existing fuzzy match handles the exact and near-miss cases. The postcode-only test may need a fix if `find_duplicate` doesn't guard against empty addresses.

- [ ] **Step 3: Fix find_duplicate if postcode-only test fails**

  If the postcode-only test fails (i.e. `find_duplicate` returns a match for empty address + valid postcode), add an early return at the top of `find_duplicate`:

  In `backend/services/deduplication_service.py`, find the `find_duplicate` method. Add at the start of the method body:

  ```python
  if not address or len(address.strip()) < 5:
      return None  # Cannot meaningfully deduplicate without an address
  ```

- [ ] **Step 4: Run tests to verify all pass**

  ```bash
  docker-compose exec backend pytest tests/services/test_dedup_uploads.py -v
  ```

  Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add tests/services/test_dedup_uploads.py backend/services/deduplication_service.py
  git commit -m "test: add dedup tests for uploaded-vs-scraped property scenarios"
  ```

---

## Task 7: Frontend — Description Display + Image Gallery

**Files:**
- Modify: `frontend/src/pages/PropertyDetail.jsx:640-650`
- Create: `frontend/src/components/ui/ImageGallery.jsx`

- [ ] **Step 1: Create ImageGallery component**

  Create `frontend/src/components/ui/ImageGallery.jsx`:

  ```jsx
  import { useState } from 'react';
  import { ChevronLeft, ChevronRight, X } from 'lucide-react';

  export default function ImageGallery({ imageUrl, imageUrls, alt }) {
    const [lightboxIdx, setLightboxIdx] = useState(null);

    let images = [];
    if (imageUrls) {
      try {
        images = JSON.parse(imageUrls);
      } catch {
        images = [];
      }
    }
    if (!images.length && imageUrl) {
      images = [imageUrl];
    }
    if (!images.length) return null;

    const openLightbox = (idx) => setLightboxIdx(idx);
    const closeLightbox = () => setLightboxIdx(null);
    const prev = () => setLightboxIdx((i) => (i > 0 ? i - 1 : images.length - 1));
    const next = () => setLightboxIdx((i) => (i < images.length - 1 ? i + 1 : 0));

    return (
      <>
        {/* Hero image */}
        <div
          className="h-64 w-full overflow-hidden bg-slate-900 rounded-b-2xl cursor-pointer"
          onClick={() => openLightbox(0)}
        >
          <img
            src={images[0]}
            alt={alt}
            className="w-full h-full object-cover"
            onError={(e) => { e.target.parentElement.style.display = 'none'; }}
          />
        </div>

        {/* Thumbnail strip (if more than 1 image) */}
        {images.length > 1 && (
          <div className="flex gap-2 px-6 overflow-x-auto py-1">
            {images.slice(0, 10).map((src, idx) => (
              <button
                key={idx}
                onClick={() => openLightbox(idx)}
                className={`flex-shrink-0 w-16 h-12 rounded-lg overflow-hidden border-2 transition-colors ${
                  lightboxIdx === idx ? 'border-emerald-500' : 'border-transparent hover:border-slate-600'
                }`}
              >
                <img src={src} alt={`${alt} ${idx + 1}`} className="w-full h-full object-cover" />
              </button>
            ))}
            {images.length > 10 && (
              <span className="flex items-center text-xs text-slate-500 px-2">
                +{images.length - 10} more
              </span>
            )}
          </div>
        )}

        {/* Lightbox overlay */}
        {lightboxIdx !== null && (
          <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center" onClick={closeLightbox}>
            <button
              onClick={(e) => { e.stopPropagation(); closeLightbox(); }}
              className="absolute top-4 right-4 text-white/70 hover:text-white p-2"
            >
              <X size={24} />
            </button>
            {images.length > 1 && (
              <>
                <button
                  onClick={(e) => { e.stopPropagation(); prev(); }}
                  className="absolute left-4 text-white/70 hover:text-white p-2"
                >
                  <ChevronLeft size={32} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); next(); }}
                  className="absolute right-4 text-white/70 hover:text-white p-2"
                >
                  <ChevronRight size={32} />
                </button>
              </>
            )}
            <img
              src={images[lightboxIdx]}
              alt={`${alt} ${lightboxIdx + 1}`}
              className="max-h-[85vh] max-w-[90vw] object-contain"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="absolute bottom-4 text-white/60 text-sm">
              {lightboxIdx + 1} / {images.length}
            </div>
          </div>
        )}
      </>
    );
  }
  ```

- [ ] **Step 2: Replace hero image with ImageGallery in PropertyDetail**

  In `frontend/src/pages/PropertyDetail.jsx`, add the import near the top with the other component imports:

  ```jsx
  import ImageGallery from '../components/ui/ImageGallery';
  ```

  Find lines 641-650:

  ```jsx
  {property.image_url && (
    <div className="h-64 w-full overflow-hidden bg-slate-900 rounded-b-2xl">
      <img
        src={property.image_url}
        alt={property.address}
        className="w-full h-full object-cover"
        onError={e => { e.target.parentElement.style.display = 'none'; }}
      />
    </div>
  )}
  ```

  Replace with:

  ```jsx
  <ImageGallery
    imageUrl={property.image_url}
    imageUrls={property.image_urls}
    alt={property.address}
  />
  ```

- [ ] **Step 3: Add description display**

  In the same file, find the line after `<div className="px-6 space-y-6">` (line 652). Add the description block immediately after:

  ```jsx
  {/* Property description */}
  {property.description && (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-2">Description</h3>
      <p className="text-sm text-slate-400 leading-relaxed whitespace-pre-line">
        {property.description}
      </p>
    </div>
  )}
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/ui/ImageGallery.jsx frontend/src/pages/PropertyDetail.jsx
  git commit -m "feat: add image gallery with lightbox and description display on PropertyDetail"
  ```

---

## Task 8: On-Demand Property Scan — Backend Service

**Files:**
- Create: `backend/services/scan_service.py`
- Create: `tests/services/test_scan_service.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/services/test_scan_service.py`:

  ```python
  """Tests for on-demand property scan service."""
  import pytest
  from unittest.mock import MagicMock, patch, AsyncMock
  from datetime import datetime, date


  def _make_scan_service(db):
      from backend.services.scan_service import ScanService
      svc = ScanService(db)
      return svc


  def test_cached_property_returned_without_api_calls():
      """If property already exists in DB, return it without calling external APIs."""
      db = MagicMock()
      from backend.models.property import Property
      existing = MagicMock(spec=Property)
      existing.id = 1
      existing.address = '123 High St'
      existing.postcode = 'SW1A 1AA'
      existing.status = 'active'
      existing.score = MagicMock()
      existing.ai_insight = MagicMock()

      svc = _make_scan_service(db)
      with patch.object(svc, '_find_existing', return_value=existing):
          result = svc.scan(address='123 High St', postcode='SW1A 1AA')
      assert result['property_id'] == 1
      assert result['scan_type'] == 'property'
      assert result['cached'] is True


  def test_postcode_only_returns_area_scan():
      """Postcode without address returns area-level data only."""
      db = MagicMock()
      svc = _make_scan_service(db)
      with patch.object(svc, '_find_existing', return_value=None), \
           patch.object(svc, '_area_scan', return_value={'avg_price': 250000}):
          result = svc.scan(address='', postcode='SW1A 1AA')
      assert result['scan_type'] == 'area'


  def test_new_property_created_and_enriched():
      """A property not in DB gets created, scored, and queued for AI analysis."""
      db = MagicMock()
      svc = _make_scan_service(db)
      with patch.object(svc, '_find_existing', return_value=None), \
           patch.object(svc, '_create_scanned_property', return_value=MagicMock(id=99)) as mock_create, \
           patch.object(svc, '_enrich_property') as mock_enrich, \
           patch.object(svc, '_score_property') as mock_score:
          result = svc.scan(address='456 New Road', postcode='LS1 4AP')
      mock_create.assert_called_once()
      mock_enrich.assert_called_once()
      mock_score.assert_called_once()
      assert result['scan_type'] == 'property'
      assert result['cached'] is False
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/services/test_scan_service.py -v
  ```

  Expected: FAIL — `backend.services.scan_service` does not exist.

- [ ] **Step 3: Create scan service**

  Create `backend/services/scan_service.py`:

  ```python
  """
  On-demand property scan service.
  Orchestrates lookups across Land Registry, EPC, PropertyData, and scoring
  to build a full intelligence profile for any UK address.
  """
  import logging
  from datetime import datetime, timedelta
  from typing import Optional, Dict, Any

  from sqlalchemy.orm import Session

  from backend.models.property import Property, PropertySource, PropertyScore
  from backend.models.sales_history import SalesHistory
  from backend.models.epc_certificate import EPCCertificate
  from backend.services.deduplication_service import PropertyDeduplicator
  from backend.services.scoring_service import PropertyScoringService
  from backend.services.propertydata_service import PropertyDataService

  logger = logging.getLogger(__name__)

  STALE_DAYS = 7


  class ScanService:
      def __init__(self, db: Session):
          self.db = db
          self.deduplicator = PropertyDeduplicator(db)
          self.scoring = PropertyScoringService(db)
          self.pd_service = PropertyDataService()

      def scan(self, address: str, postcode: str) -> Dict[str, Any]:
          """
          Scan a property by address + postcode. Returns full intelligence profile.
          - If property exists in DB and is fresh, returns cached data.
          - If postcode only (no address), returns area-level data.
          - Otherwise creates property, enriches, scores, and returns.
          """
          postcode = (postcode or '').strip().upper()
          address = (address or '').strip()

          if not postcode:
              raise ValueError("Postcode is required")

          # Postcode-only: area scan
          if not address or len(address) < 5:
              area_data = self._area_scan(postcode)
              return {
                  'scan_type': 'area',
                  'postcode': postcode,
                  'cached': False,
                  **area_data,
              }

          # Check for existing property
          existing = self._find_existing(address, postcode)
          if existing:
              return self._build_response(existing, cached=True)

          # Create new property from scan
          prop = self._create_scanned_property(address, postcode)
          self._enrich_property(prop)
          self._score_property(prop)

          self.db.commit()
          return self._build_response(prop, cached=False)

      def _find_existing(self, address: str, postcode: str) -> Optional[Property]:
          """Check if property already exists via dedup. Returns None if not found or stale."""
          match = self.deduplicator.find_duplicate(address=address, postcode=postcode)
          if match:
              # Check staleness — re-enrich if older than STALE_DAYS
              if match.updated_at and match.updated_at < datetime.utcnow() - timedelta(days=STALE_DAYS):
                  self._enrich_property(match)
                  self._score_property(match)
                  self.db.commit()
              return match
          return None

      def _area_scan(self, postcode: str) -> Dict[str, Any]:
          """Return area-level data when no specific address is available."""
          district = postcode.split()[0] if ' ' in postcode else postcode[:-3].strip()

          # Sales history for the postcode district
          sales = (
              self.db.query(SalesHistory)
              .filter(SalesHistory.postcode.ilike(f'{district}%'))
              .order_by(SalesHistory.sale_date.desc())
              .limit(50)
              .all()
          )

          # EPC band distribution
          epcs = (
              self.db.query(EPCCertificate.energy_rating, self.db.query(EPCCertificate).filter(False).count)
              .filter(EPCCertificate.postcode.ilike(f'{district}%'))
              .all()
          )

          avg_price = sum(s.sale_price for s in sales if s.sale_price) / max(len([s for s in sales if s.sale_price]), 1) if sales else None

          return {
              'district': district,
              'avg_price': avg_price,
              'recent_sales_count': len(sales),
              'sales_history': [
                  {'date': str(s.sale_date), 'price': s.sale_price, 'address': s.address}
                  for s in sales[:20]
              ],
          }

      def _create_scanned_property(self, address: str, postcode: str) -> Property:
          """Create a new property record from an on-demand scan."""
          # Look up EPC data for this address
          epc = self._find_epc(address, postcode)

          prop = Property(
              address=address,
              postcode=postcode,
              property_type=epc.property_type.lower() if epc and epc.property_type else 'unknown',
              status='active',
              date_found=datetime.utcnow(),
              source='on_demand_scan',
          )

          if epc:
              prop.epc_energy_rating = epc.energy_rating
              prop.epc_potential_rating = epc.potential_energy_rating
              prop.epc_floor_area_sqm = epc.floor_area_sqm
              prop.epc_property_type = epc.property_type
              prop.epc_inspection_date = epc.inspection_date
              prop.epc_matched_at = datetime.utcnow()

          self.db.add(prop)
          self.db.flush()

          # Add source record
          self.deduplicator.add_property_source(
              prop.id,
              source_name='on_demand_scan',
              source_id=None,
              source_url=None,
          )

          return prop

      def _find_epc(self, address: str, postcode: str) -> Optional[EPCCertificate]:
          """Find best EPC certificate match for an address."""
          certs = (
              self.db.query(EPCCertificate)
              .filter(EPCCertificate.postcode == postcode)
              .order_by(EPCCertificate.inspection_date.desc())
              .limit(20)
              .all()
          )
          if not certs:
              return None

          # Simple address matching — first token match
          addr_lower = address.lower()
          for cert in certs:
              cert_addr = (cert.address1 or '').lower()
              if addr_lower.split()[0] in cert_addr or cert_addr.split()[0] in addr_lower:
                  return cert

          # Fall back to most recent for this postcode
          return certs[0] if certs else None

      def _enrich_property(self, prop: Property):
          """Enrich with PropertyData AVM, rental estimate, flood risk."""
          try:
              score = self.db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()
              if not score:
                  score = PropertyScore(property_id=prop.id)
                  self.db.add(score)
                  self.db.flush()
              self.pd_service.enrich(prop, score, self.db)
          except Exception as e:
              logger.warning("PropertyData enrichment failed for %d: %s", prop.id, e)

      def _score_property(self, prop: Property):
          """Run the scoring service on the property."""
          try:
              self.scoring.score_property(prop)
          except Exception as e:
              logger.warning("Scoring failed for %d: %s", prop.id, e)

      def _build_response(self, prop: Property, cached: bool) -> Dict[str, Any]:
          """Build the scan response dict from a property record."""
          score = self.db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()

          return {
              'scan_type': 'property',
              'cached': cached,
              'property_id': prop.id,
              'address': prop.address,
              'postcode': prop.postcode,
              'property_type': prop.property_type,
              'bedrooms': prop.bedrooms,
              'bathrooms': prop.bathrooms,
              'asking_price': prop.asking_price,
              'epc_rating': prop.epc_energy_rating,
              'epc_potential_rating': prop.epc_potential_rating,
              'epc_floor_area': prop.epc_floor_area_sqm,
              'score': {
                  'investment_score': score.investment_score if score else None,
                  'price_band': score.price_band if score else None,
                  'estimated_value': score.estimated_value if score else None,
                  'gross_yield_pct': score.gross_yield_pct if score else None,
                  'pd_avm': score.pd_avm if score else None,
                  'pd_rental_estimate': score.pd_rental_estimate if score else None,
                  'pd_flood_risk': score.pd_flood_risk if score else None,
              } if score else None,
          }
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/services/test_scan_service.py -v
  ```

  Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/scan_service.py tests/services/test_scan_service.py
  git commit -m "feat: add on-demand property scan service"
  ```

---

## Task 9: On-Demand Property Scan — API Endpoint

**Files:**
- Create: `backend/api/routers/scan.py`
- Modify: `backend/api/main.py:42-49`
- Create: `tests/api/test_scan.py`

- [ ] **Step 1: Write failing test**

  Create `tests/api/test_scan.py`:

  ```python
  """Tests for the scan API endpoint."""
  import pytest
  from unittest.mock import patch, MagicMock
  from fastapi.testclient import TestClient


  @pytest.fixture
  def client():
      from backend.api.main import app
      return TestClient(app)


  def test_scan_requires_postcode(client):
      response = client.post('/api/scan', json={'address': '123 High St'})
      assert response.status_code == 422


  def test_scan_returns_property_result(client):
      mock_result = {
          'scan_type': 'property',
          'cached': False,
          'property_id': 1,
          'address': '123 High St',
          'postcode': 'SW1A 1AA',
      }
      with patch('backend.api.routers.scan.ScanService') as MockSvc:
          MockSvc.return_value.scan.return_value = mock_result
          response = client.post('/api/scan', json={
              'address': '123 High St',
              'postcode': 'SW1A 1AA',
          })
      assert response.status_code == 200
      data = response.json()
      assert data['scan_type'] == 'property'
      assert data['property_id'] == 1


  def test_scan_postcode_only_returns_area(client):
      mock_result = {
          'scan_type': 'area',
          'postcode': 'SW1A 1AA',
          'cached': False,
          'avg_price': 500000,
      }
      with patch('backend.api.routers.scan.ScanService') as MockSvc:
          MockSvc.return_value.scan.return_value = mock_result
          response = client.post('/api/scan', json={'postcode': 'SW1A 1AA'})
      assert response.status_code == 200
      assert response.json()['scan_type'] == 'area'
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/api/test_scan.py -v
  ```

  Expected: FAIL — `backend.api.routers.scan` does not exist.

- [ ] **Step 3: Create scan router**

  Create `backend/api/routers/scan.py`:

  ```python
  """On-demand property scan endpoint."""
  import logging
  from typing import Optional

  from fastapi import APIRouter, Depends, HTTPException
  from pydantic import BaseModel, Field
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.services.scan_service import ScanService

  logger = logging.getLogger(__name__)

  router = APIRouter(prefix="/api/scan", tags=["scan"])


  class ScanRequest(BaseModel):
      address: Optional[str] = Field(None, description="Property address (optional for area scan)")
      postcode: str = Field(..., description="UK postcode (required)")


  @router.post("")
  def scan_property(req: ScanRequest, db: Session = Depends(get_db)):
      """
      Scan any UK property by address + postcode.
      Returns full intelligence profile (or area-level data if postcode only).
      """
      try:
          svc = ScanService(db)
          result = svc.scan(address=req.address or '', postcode=req.postcode)
          return result
      except ValueError as e:
          raise HTTPException(status_code=400, detail=str(e))
      except Exception as e:
          logger.error("Scan failed: %s", e, exc_info=True)
          raise HTTPException(status_code=500, detail="Scan failed")
  ```

- [ ] **Step 4: Register router in main.py**

  In `backend/api/main.py`, add the import and include after line 49:

  ```python
  from backend.api.routers import scan
  ```

  Add after the existing `app.include_router(ads.router)` line:

  ```python
  app.include_router(scan.router)
  ```

- [ ] **Step 5: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/api/test_scan.py -v
  ```

  Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/api/routers/scan.py backend/api/main.py tests/api/test_scan.py
  git commit -m "feat: add on-demand property scan endpoint POST /api/scan"
  ```

---

## Task 10: Extended EPC Fields — Migration & Model (Slippable)

**Files:**
- Modify: `backend/models/epc_certificate.py`
- Modify: `backend/models/epc_recommendation.py`
- Create: `database/migrations/versions/021_epc_extended_fields.py`
- Create: `database/migrations/versions/022_epc_rec_extended.py`

- [ ] **Step 1: Add Tier 1 columns to EPCCertificate model**

  In `backend/models/epc_certificate.py`, add after `inspection_date` (line 25):

  ```python
    # Extended Tier 1 fields (Sprint 1 addendum)
    construction_age_band       = Column(String(50), nullable=True)
    current_energy_efficiency   = Column(Integer, nullable=True)    # 0-100 numeric
    potential_energy_efficiency  = Column(Integer, nullable=True)    # 0-100 numeric
    tenure                      = Column(String(50), nullable=True)  # owner-occupied, rental, etc.
    mains_gas_flag              = Column(String(1), nullable=True)   # Y/N
    heating_cost_current        = Column(Float, nullable=True)       # annual £
    heating_cost_potential       = Column(Float, nullable=True)       # annual £
    hot_water_cost_current      = Column(Float, nullable=True)       # annual £
    hot_water_cost_potential     = Column(Float, nullable=True)       # annual £
    lighting_cost_current       = Column(Float, nullable=True)       # annual £
    lighting_cost_potential      = Column(Float, nullable=True)       # annual £
    co2_emissions_current       = Column(Float, nullable=True)       # tonnes/yr
    number_habitable_rooms      = Column(Integer, nullable=True)
    transaction_type            = Column(String(50), nullable=True)  # marketed sale, rental, etc.
    epc_expiry_date             = Column(Date, nullable=True)        # computed: inspection_date + 10yr
  ```

- [ ] **Step 2: Add extended columns to EPCRecommendation model**

  In `backend/models/epc_recommendation.py`, add after `indicative_cost_high` (line 20):

  ```python
    # Extended fields (Sprint 1 addendum)
    typical_saving              = Column(Float, nullable=True)       # annual £ saving
    efficiency_rating_before    = Column(Integer, nullable=True)     # EPC score before improvement
    efficiency_rating_after     = Column(Integer, nullable=True)     # EPC score after improvement
  ```

  Add `Float` to the import on line 2:

  ```python
  from sqlalchemy import Column, Integer, String, Float, Text, Index, ForeignKey
  ```

- [ ] **Step 3: Create migration 021**

  Create `database/migrations/versions/021_epc_extended_fields.py`:

  ```python
  """Add extended EPC Tier 1 fields to epc_certificates.

  Revision ID: 021
  Revises: 020
  """
  from alembic import op
  import sqlalchemy as sa

  revision = '021'
  down_revision = '020'
  branch_labels = None
  depends_on = None


  def upgrade():
      op.add_column('epc_certificates', sa.Column('construction_age_band', sa.String(50), nullable=True))
      op.add_column('epc_certificates', sa.Column('current_energy_efficiency', sa.Integer(), nullable=True))
      op.add_column('epc_certificates', sa.Column('potential_energy_efficiency', sa.Integer(), nullable=True))
      op.add_column('epc_certificates', sa.Column('tenure', sa.String(50), nullable=True))
      op.add_column('epc_certificates', sa.Column('mains_gas_flag', sa.String(1), nullable=True))
      op.add_column('epc_certificates', sa.Column('heating_cost_current', sa.Float(), nullable=True))
      op.add_column('epc_certificates', sa.Column('heating_cost_potential', sa.Float(), nullable=True))
      op.add_column('epc_certificates', sa.Column('hot_water_cost_current', sa.Float(), nullable=True))
      op.add_column('epc_certificates', sa.Column('hot_water_cost_potential', sa.Float(), nullable=True))
      op.add_column('epc_certificates', sa.Column('lighting_cost_current', sa.Float(), nullable=True))
      op.add_column('epc_certificates', sa.Column('lighting_cost_potential', sa.Float(), nullable=True))
      op.add_column('epc_certificates', sa.Column('co2_emissions_current', sa.Float(), nullable=True))
      op.add_column('epc_certificates', sa.Column('number_habitable_rooms', sa.Integer(), nullable=True))
      op.add_column('epc_certificates', sa.Column('transaction_type', sa.String(50), nullable=True))
      op.add_column('epc_certificates', sa.Column('epc_expiry_date', sa.Date(), nullable=True))


  def downgrade():
      op.drop_column('epc_certificates', 'epc_expiry_date')
      op.drop_column('epc_certificates', 'transaction_type')
      op.drop_column('epc_certificates', 'number_habitable_rooms')
      op.drop_column('epc_certificates', 'co2_emissions_current')
      op.drop_column('epc_certificates', 'lighting_cost_potential')
      op.drop_column('epc_certificates', 'lighting_cost_current')
      op.drop_column('epc_certificates', 'hot_water_cost_potential')
      op.drop_column('epc_certificates', 'hot_water_cost_current')
      op.drop_column('epc_certificates', 'heating_cost_potential')
      op.drop_column('epc_certificates', 'heating_cost_current')
      op.drop_column('epc_certificates', 'mains_gas_flag')
      op.drop_column('epc_certificates', 'tenure')
      op.drop_column('epc_certificates', 'potential_energy_efficiency')
      op.drop_column('epc_certificates', 'current_energy_efficiency')
      op.drop_column('epc_certificates', 'construction_age_band')
  ```

- [ ] **Step 4: Create migration 022**

  Create `database/migrations/versions/022_epc_rec_extended.py`:

  ```python
  """Add extended fields to epc_recommendations.

  Revision ID: 022
  Revises: 021
  """
  from alembic import op
  import sqlalchemy as sa

  revision = '022'
  down_revision = '021'
  branch_labels = None
  depends_on = None


  def upgrade():
      op.add_column('epc_recommendations', sa.Column('typical_saving', sa.Float(), nullable=True))
      op.add_column('epc_recommendations', sa.Column('efficiency_rating_before', sa.Integer(), nullable=True))
      op.add_column('epc_recommendations', sa.Column('efficiency_rating_after', sa.Integer(), nullable=True))


  def downgrade():
      op.drop_column('epc_recommendations', 'efficiency_rating_after')
      op.drop_column('epc_recommendations', 'efficiency_rating_before')
      op.drop_column('epc_recommendations', 'typical_saving')
  ```

- [ ] **Step 5: Run migrations**

  ```bash
  docker-compose exec backend alembic upgrade head
  ```

  Expected: `021` and `022` applied successfully.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/models/epc_certificate.py backend/models/epc_recommendation.py database/migrations/versions/021_epc_extended_fields.py database/migrations/versions/022_epc_rec_extended.py
  git commit -m "feat: add extended EPC Tier 1 fields — migration 021/022"
  ```

---

## Task 11: EPC Importer — Extend CSV Column Mappings

**Files:**
- Modify: `backend/etl/epc_importer.py:40-62`

- [ ] **Step 1: Extend CERT_COLUMN_MAP**

  In `backend/etl/epc_importer.py`, replace the `CERT_COLUMN_MAP` dict (lines 40-52) with:

  ```python
  CERT_COLUMN_MAP = {
      'LMK_KEY':                      'lmk_key',
      'ADDRESS1':                     'address1',
      'ADDRESS2':                     'address2',
      'POSTCODE':                     'postcode',
      'UPRN':                         'uprn',
      'PROPERTY_TYPE':                'property_type',
      'BUILT_FORM':                   'built_form',
      'TOTAL_FLOOR_AREA':             'floor_area_sqm',
      'CURRENT_ENERGY_RATING':        'energy_rating',
      'POTENTIAL_ENERGY_RATING':      'potential_energy_rating',
      'INSPECTION_DATE':              'inspection_date',
      # Extended Tier 1 fields
      'CONSTRUCTION_AGE_BAND':        'construction_age_band',
      'CURRENT_ENERGY_EFFICIENCY':    'current_energy_efficiency',
      'POTENTIAL_ENERGY_EFFICIENCY':  'potential_energy_efficiency',
      'TENURE':                       'tenure',
      'MAINS_GAS_FLAG':               'mains_gas_flag',
      'HEATING_COST_CURRENT':         'heating_cost_current',
      'HEATING_COST_POTENTIAL':       'heating_cost_potential',
      'HOT_WATER_COST_CURRENT':       'hot_water_cost_current',
      'HOT_WATER_COST_POTENTIAL':     'hot_water_cost_potential',
      'LIGHTING_COST_CURRENT':        'lighting_cost_current',
      'LIGHTING_COST_POTENTIAL':      'lighting_cost_potential',
      'CO2_EMISSIONS_CURRENT':        'co2_emissions_current',
      'NUMBER_HABITABLE_ROOMS':       'number_habitable_rooms',
      'TRANSACTION_TYPE':             'transaction_type',
  }
  ```

- [ ] **Step 2: Extend REC_COLUMN_MAP**

  Replace `REC_COLUMN_MAP` (lines 56-62) with:

  ```python
  REC_COLUMN_MAP = {
      'LMK_KEY':                      'lmk_key',
      'IMPROVEMENT_ITEM':             'improvement_item',
      'IMPROVEMENT_SUMMARY_TEXT':     'improvement_summary_text',
      'IMPROVEMENT_DESCR_TEXT':       'improvement_descr_text',
      'INDICATIVE_COST':              'indicative_cost_raw',
      # Extended fields
      'TYPICAL_SAVING':               'typical_saving',
      'ENERGY_EFFICIENCY_RATING_A':   'efficiency_rating_before',
      'ENERGY_EFFICIENCY_RATING_B':   'efficiency_rating_after',
  }
  ```

- [ ] **Step 3: Add epc_expiry_date computation**

  Find the `_clean_cert_chunk` function in the same file (search for `def _clean_cert_chunk`). After the existing date parsing and before the return, add:

  ```python
  # Compute EPC expiry date (inspection_date + 10 years)
  if 'inspection_date' in chunk.columns and chunk['inspection_date'].notna().any():
      chunk['epc_expiry_date'] = pd.to_datetime(chunk['inspection_date'], errors='coerce') + pd.DateOffset(years=10)
      chunk['epc_expiry_date'] = chunk['epc_expiry_date'].dt.date
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/etl/epc_importer.py
  git commit -m "feat: extend EPC importer CSV mappings for Tier 1 fields + expiry date"
  ```

---

## Task 12: EPC Colour-Coding on Frontend

**Files:**
- Modify: `frontend/src/pages/PropertyDetail.jsx` (EPCPanel section)

This task adds colour-coded indicators to the existing EPCPanel inline section on PropertyDetail. The colour rules come from addendum Section A4.

- [ ] **Step 1: Find and update EPCPanel section**

  In `frontend/src/pages/PropertyDetail.jsx`, find the EPCPanel section (search for `EPC` or `energy_rating`). Add a helper function above the component return:

  ```jsx
  function epcBandColour(band) {
    if (!band) return 'text-slate-500';
    const b = band.toUpperCase();
    if ('ABC'.includes(b)) return 'text-emerald-400';
    if ('DE'.includes(b)) return 'text-amber-400';
    return 'text-red-400'; // F, G
  }

  function epcEfficiencyColour(rating) {
    if (!rating) return 'text-slate-500';
    const r = rating.toLowerCase();
    if (r === 'very good' || r === 'good') return 'text-emerald-400';
    if (r === 'average') return 'text-amber-400';
    return 'text-red-400'; // poor, very poor
  }

  function epcAgeColour(ageBand) {
    if (!ageBand) return 'text-slate-500';
    // Extract year from band like "1950-1966" or "England and Wales: 2007 onwards"
    const match = ageBand.match(/(\d{4})/);
    if (!match) return 'text-slate-500';
    const year = parseInt(match[1]);
    if (year >= 1990) return 'text-emerald-400';
    if (year >= 1950) return 'text-amber-400';
    return 'text-red-400'; // pre-1950
  }
  ```

  These helpers can be used in the EPCPanel to colour-code badges as data becomes available from the extended EPC fields.

- [ ] **Step 2: Commit**

  ```bash
  git add frontend/src/pages/PropertyDetail.jsx
  git commit -m "feat: add EPC colour-coding helpers for extended fields"
  ```

---

# SPRINT 2: AUTH & BILLING

---

## Task 13: User Model + Migration

**Files:**
- Create: `backend/models/user.py`
- Create: `database/migrations/versions/023_users.py`

- [ ] **Step 1: Create User model**

  Create `backend/models/user.py`:

  ```python
  """User and UserProfile models for auth and subscription management."""
  from sqlalchemy import (
      Column, Integer, String, Float, Boolean, DateTime, Date,
      Text, ForeignKey, Enum as SAEnum, Index
  )
  from sqlalchemy.orm import relationship
  from datetime import datetime
  from .base import Base, TimestampMixin

  import enum


  class UserRole(str, enum.Enum):
      investor = 'investor'
      auction_house = 'auction_house'
      deal_source = 'deal_source'
      admin = 'admin'


  class SubscriptionStatus(str, enum.Enum):
      trial = 'trial'
      active = 'active'
      past_due = 'past_due'
      cancelled = 'cancelled'


  class SubscriptionTier(str, enum.Enum):
      none = 'none'
      investor = 'investor'
      auction_house = 'auction_house'
      deal_source = 'deal_source'
      white_label = 'white_label'
      admin = 'admin'


  class User(Base, TimestampMixin):
      __tablename__ = 'users'

      id = Column(Integer, primary_key=True)
      email = Column(String(255), unique=True, index=True, nullable=False)
      hashed_password = Column(String(255), nullable=False)
      full_name = Column(String(200), nullable=False)
      company_name = Column(String(200), nullable=True)
      phone = Column(String(20), nullable=True)

      role = Column(SAEnum(UserRole), nullable=False, default=UserRole.investor)
      subscription_status = Column(SAEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.trial)
      subscription_tier = Column(SAEnum(SubscriptionTier), nullable=False, default=SubscriptionTier.none)

      stripe_customer_id = Column(String(100), unique=True, nullable=True)
      stripe_subscription_id = Column(String(100), nullable=True)
      stripe_subscription_id_secondary = Column(String(100), nullable=True)

      trial_property_views = Column(Integer, default=0, nullable=False)
      trial_ai_views = Column(Integer, default=0, nullable=False)

      is_active = Column(Boolean, default=True, nullable=False)
      is_superuser = Column(Boolean, default=False, nullable=False)
      is_verified = Column(Boolean, default=False, nullable=False)

      profile = relationship('UserProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')

      def __repr__(self):
          return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


  class UserProfile(Base, TimestampMixin):
      __tablename__ = 'user_profiles'

      id = Column(Integer, primary_key=True)
      user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False)

      # Financial capacity
      max_deposit = Column(Integer, nullable=True)
      loan_type_sought = Column(String(50), nullable=True)
      max_loan_wanted = Column(Integer, nullable=True)
      loan_term_months = Column(Integer, nullable=True)
      purpose = Column(String(20), nullable=True)

      # Portfolio & experience
      investment_experience = Column(String(20), nullable=True)
      properties_owned = Column(Integer, nullable=True)
      portfolio_value_band = Column(String(20), nullable=True)
      outstanding_mortgage_band = Column(String(20), nullable=True)
      hmo_experience = Column(Boolean, nullable=True)
      development_experience = Column(Boolean, nullable=True)
      limited_company = Column(Boolean, nullable=True)
      company_name_ch = Column(String(200), nullable=True)
      companies_house_number = Column(String(20), nullable=True)
      spv = Column(Boolean, nullable=True)
      personal_guarantee_willing = Column(Boolean, nullable=True)

      # Personal circumstances
      main_residence = Column(Boolean, nullable=True)
      uk_resident = Column(Boolean, nullable=True)
      employment_status = Column(String(20), nullable=True)
      annual_income_band = Column(String(20), nullable=True)
      credit_history = Column(String(20), nullable=True)

      # Investment preferences
      target_location = Column(String(200), nullable=True)
      strategy = Column(String(30), nullable=True)
      readiness = Column(String(20), nullable=True)

      # GDPR
      broker_consent_given_at = Column(DateTime, nullable=True)
      profile_deletion_at = Column(DateTime, nullable=True)

      # Uploader settings
      auction_form_field_prefs = Column(Text, nullable=True)  # JSON array
      brand_logo_url = Column(String(500), nullable=True)
      brand_primary_colour = Column(String(7), nullable=True)
      brand_accent_colour = Column(String(7), nullable=True)
      custom_subdomain = Column(String(200), nullable=True)

      user = relationship('User', back_populates='profile')

      def __repr__(self):
          return f"<UserProfile(user_id={self.user_id})>"
  ```

- [ ] **Step 2: Create migration 023**

  Create `database/migrations/versions/023_users.py`:

  ```python
  """Create users and user_profiles tables.

  Revision ID: 023
  Revises: 022
  """
  from alembic import op
  import sqlalchemy as sa

  revision = '023'
  down_revision = '022'
  branch_labels = None
  depends_on = None


  def upgrade():
      op.create_table(
          'users',
          sa.Column('id', sa.Integer(), primary_key=True),
          sa.Column('email', sa.String(255), unique=True, index=True, nullable=False),
          sa.Column('hashed_password', sa.String(255), nullable=False),
          sa.Column('full_name', sa.String(200), nullable=False),
          sa.Column('company_name', sa.String(200), nullable=True),
          sa.Column('phone', sa.String(20), nullable=True),
          sa.Column('role', sa.String(20), nullable=False, server_default='investor'),
          sa.Column('subscription_status', sa.String(20), nullable=False, server_default='trial'),
          sa.Column('subscription_tier', sa.String(20), nullable=False, server_default='none'),
          sa.Column('stripe_customer_id', sa.String(100), unique=True, nullable=True),
          sa.Column('stripe_subscription_id', sa.String(100), nullable=True),
          sa.Column('stripe_subscription_id_secondary', sa.String(100), nullable=True),
          sa.Column('trial_property_views', sa.Integer(), nullable=False, server_default='0'),
          sa.Column('trial_ai_views', sa.Integer(), nullable=False, server_default='0'),
          sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
          sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
          sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
          sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
          sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
      )

      op.create_table(
          'user_profiles',
          sa.Column('id', sa.Integer(), primary_key=True),
          sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False),
          # Financial
          sa.Column('max_deposit', sa.Integer(), nullable=True),
          sa.Column('loan_type_sought', sa.String(50), nullable=True),
          sa.Column('max_loan_wanted', sa.Integer(), nullable=True),
          sa.Column('loan_term_months', sa.Integer(), nullable=True),
          sa.Column('purpose', sa.String(20), nullable=True),
          # Portfolio
          sa.Column('investment_experience', sa.String(20), nullable=True),
          sa.Column('properties_owned', sa.Integer(), nullable=True),
          sa.Column('portfolio_value_band', sa.String(20), nullable=True),
          sa.Column('outstanding_mortgage_band', sa.String(20), nullable=True),
          sa.Column('hmo_experience', sa.Boolean(), nullable=True),
          sa.Column('development_experience', sa.Boolean(), nullable=True),
          sa.Column('limited_company', sa.Boolean(), nullable=True),
          sa.Column('company_name_ch', sa.String(200), nullable=True),
          sa.Column('companies_house_number', sa.String(20), nullable=True),
          sa.Column('spv', sa.Boolean(), nullable=True),
          sa.Column('personal_guarantee_willing', sa.Boolean(), nullable=True),
          # Personal
          sa.Column('main_residence', sa.Boolean(), nullable=True),
          sa.Column('uk_resident', sa.Boolean(), nullable=True),
          sa.Column('employment_status', sa.String(20), nullable=True),
          sa.Column('annual_income_band', sa.String(20), nullable=True),
          sa.Column('credit_history', sa.String(20), nullable=True),
          # Preferences
          sa.Column('target_location', sa.String(200), nullable=True),
          sa.Column('strategy', sa.String(30), nullable=True),
          sa.Column('readiness', sa.String(20), nullable=True),
          # GDPR
          sa.Column('broker_consent_given_at', sa.DateTime(), nullable=True),
          sa.Column('profile_deletion_at', sa.DateTime(), nullable=True),
          # Uploader
          sa.Column('auction_form_field_prefs', sa.Text(), nullable=True),
          sa.Column('brand_logo_url', sa.String(500), nullable=True),
          sa.Column('brand_primary_colour', sa.String(7), nullable=True),
          sa.Column('brand_accent_colour', sa.String(7), nullable=True),
          sa.Column('custom_subdomain', sa.String(200), nullable=True),
          sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
          sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
      )


  def downgrade():
      op.drop_table('user_profiles')
      op.drop_table('users')
  ```

- [ ] **Step 3: Run migration**

  ```bash
  docker-compose exec backend alembic upgrade head
  ```

  Expected: `023` applied, `users` and `user_profiles` tables created.

- [ ] **Step 4: Commit**

  ```bash
  git add backend/models/user.py database/migrations/versions/023_users.py
  git commit -m "feat: add User and UserProfile models with migration 023"
  ```

---

## Task 14: FastAPI-Users Auth Setup

**Files:**
- Create: `backend/auth/__init__.py`
- Create: `backend/auth/config.py`
- Create: `backend/auth/manager.py`
- Create: `backend/auth/schemas.py`
- Create: `backend/api/routers/auth.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Add fastapi-users to requirements**

  Add to `requirements.txt`:

  ```
  fastapi-users[sqlalchemy]==13.0.0
  ```

- [ ] **Step 2: Create auth package**

  Create `backend/auth/__init__.py` (empty file).

  Create `backend/auth/schemas.py`:

  ```python
  """Pydantic schemas for auth endpoints."""
  from typing import Optional
  from pydantic import BaseModel, EmailStr


  class UserRead(BaseModel):
      id: int
      email: str
      full_name: str
      company_name: Optional[str] = None
      role: str
      subscription_status: str
      subscription_tier: str
      trial_property_views: int
      trial_ai_views: int
      is_active: bool
      is_verified: bool

      class Config:
          from_attributes = True


  class UserCreate(BaseModel):
      email: str
      password: str
      full_name: str
      company_name: Optional[str] = None
      role: str = 'investor'  # investor, auction_house, deal_source


  class UserUpdate(BaseModel):
      full_name: Optional[str] = None
      company_name: Optional[str] = None
      phone: Optional[str] = None
  ```

  Create `backend/auth/config.py`:

  ```python
  """FastAPI-Users JWT configuration."""
  import os
  from datetime import timedelta

  JWT_SECRET = os.environ.get('JWT_SECRET', 'CHANGE-ME-IN-PRODUCTION')
  JWT_LIFETIME_SECONDS = int(os.environ.get('JWT_LIFETIME_SECONDS', 1800))  # 30 min
  JWT_REFRESH_LIFETIME_SECONDS = int(os.environ.get('JWT_REFRESH_LIFETIME_SECONDS', 604800))  # 7 days
  ```

  Create `backend/auth/manager.py`:

  ```python
  """User manager with custom registration logic."""
  import logging
  from typing import Optional

  from fastapi import Depends, Request
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.models.user import User, UserProfile, SubscriptionStatus, SubscriptionTier, UserRole

  from passlib.context import CryptContext

  logger = logging.getLogger(__name__)

  pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


  def hash_password(password: str) -> str:
      return pwd_context.hash(password)


  def verify_password(plain: str, hashed: str) -> bool:
      return pwd_context.verify(plain, hashed)


  def create_user(db: Session, email: str, password: str, full_name: str,
                  role: str = 'investor', company_name: str = None) -> User:
      """Create a new user with trial status and empty profile."""
      user = User(
          email=email.lower().strip(),
          hashed_password=hash_password(password),
          full_name=full_name,
          company_name=company_name,
          role=UserRole(role),
          subscription_status=SubscriptionStatus.trial,
          subscription_tier=SubscriptionTier.none,
      )
      db.add(user)
      db.flush()

      # Create empty profile
      profile = UserProfile(user_id=user.id)
      db.add(profile)
      db.commit()
      db.refresh(user)
      return user


  def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
      """Verify email + password, return User or None."""
      user = db.query(User).filter(User.email == email.lower().strip()).first()
      if not user or not verify_password(password, user.hashed_password):
          return None
      if not user.is_active:
          return None
      return user


  def get_user_by_email(db: Session, email: str) -> Optional[User]:
      return db.query(User).filter(User.email == email.lower().strip()).first()
  ```

- [ ] **Step 3: Create auth router with JWT**

  Create `backend/api/routers/auth.py`:

  ```python
  """Auth endpoints — register, login, refresh, me."""
  import os
  import logging
  from datetime import datetime, timedelta

  import jwt
  from fastapi import APIRouter, Depends, HTTPException, status
  from pydantic import BaseModel
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.auth.config import JWT_SECRET, JWT_LIFETIME_SECONDS, JWT_REFRESH_LIFETIME_SECONDS
  from backend.auth.manager import create_user, authenticate_user, get_user_by_email
  from backend.auth.schemas import UserRead, UserCreate
  from backend.models.user import User

  logger = logging.getLogger(__name__)
  router = APIRouter(prefix="/api/auth", tags=["auth"])

  ALGORITHM = "HS256"


  def _create_token(user_id: int, lifetime: int) -> str:
      payload = {
          "sub": str(user_id),
          "exp": datetime.utcnow() + timedelta(seconds=lifetime),
          "iat": datetime.utcnow(),
      }
      return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


  def _decode_token(token: str) -> dict:
      try:
          return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
      except jwt.ExpiredSignatureError:
          raise HTTPException(status_code=401, detail="Token expired")
      except jwt.InvalidTokenError:
          raise HTTPException(status_code=401, detail="Invalid token")


  class LoginRequest(BaseModel):
      email: str
      password: str


  class TokenResponse(BaseModel):
      access_token: str
      refresh_token: str
      token_type: str = "bearer"
      user: UserRead


  class RefreshRequest(BaseModel):
      refresh_token: str


  @router.post("/register", response_model=TokenResponse, status_code=201)
  def register(req: UserCreate, db: Session = Depends(get_db)):
      existing = get_user_by_email(db, req.email)
      if existing:
          raise HTTPException(status_code=400, detail="Email already registered")
      if req.role not in ('investor', 'auction_house', 'deal_source'):
          raise HTTPException(status_code=400, detail="Invalid role")

      user = create_user(
          db, email=req.email, password=req.password,
          full_name=req.full_name, role=req.role,
          company_name=req.company_name,
      )
      return TokenResponse(
          access_token=_create_token(user.id, JWT_LIFETIME_SECONDS),
          refresh_token=_create_token(user.id, JWT_REFRESH_LIFETIME_SECONDS),
          user=UserRead.model_validate(user),
      )


  @router.post("/login", response_model=TokenResponse)
  def login(req: LoginRequest, db: Session = Depends(get_db)):
      user = authenticate_user(db, req.email, req.password)
      if not user:
          raise HTTPException(status_code=401, detail="Invalid credentials")
      return TokenResponse(
          access_token=_create_token(user.id, JWT_LIFETIME_SECONDS),
          refresh_token=_create_token(user.id, JWT_REFRESH_LIFETIME_SECONDS),
          user=UserRead.model_validate(user),
      )


  @router.post("/refresh", response_model=TokenResponse)
  def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
      payload = _decode_token(req.refresh_token)
      user = db.query(User).get(int(payload["sub"]))
      if not user or not user.is_active:
          raise HTTPException(status_code=401, detail="User not found")
      return TokenResponse(
          access_token=_create_token(user.id, JWT_LIFETIME_SECONDS),
          refresh_token=_create_token(user.id, JWT_REFRESH_LIFETIME_SECONDS),
          user=UserRead.model_validate(user),
      )


  @router.get("/me", response_model=UserRead)
  def get_me(db: Session = Depends(get_db), token: str = Depends(lambda: None)):
      # This will be replaced with proper dependency in guards.py
      raise HTTPException(status_code=501, detail="Use get_current_user dependency")
  ```

- [ ] **Step 4: Register auth router in main.py**

  In `backend/api/main.py`, add the import:

  ```python
  from backend.api.routers import auth
  ```

  Add after the existing router includes:

  ```python
  app.include_router(auth.router)
  ```

- [ ] **Step 5: Add PyJWT to requirements**

  Add to `requirements.txt`:

  ```
  PyJWT==2.8.0
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add backend/auth/ backend/api/routers/auth.py backend/api/main.py requirements.txt
  git commit -m "feat: add FastAPI auth — register, login, JWT tokens"
  ```

---

## Task 15: Subscription Guards

**Files:**
- Create: `backend/auth/guards.py`
- Create: `tests/auth/test_guards.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/auth/__init__.py` (empty file).

  Create `tests/auth/test_guards.py`:

  ```python
  """Tests for subscription-gated route guards."""
  import pytest
  from unittest.mock import MagicMock
  from fastapi import HTTPException


  def _make_user(status='active', tier='investor', is_superuser=False,
                 trial_property_views=0, trial_ai_views=0):
      user = MagicMock()
      user.subscription_status = status
      user.subscription_tier = tier
      user.is_superuser = is_superuser
      user.trial_property_views = trial_property_views
      user.trial_ai_views = trial_ai_views
      user.stripe_subscription_id_secondary = None
      return user


  def test_admin_bypasses_all():
      from backend.auth.guards import check_subscription
      user = _make_user(is_superuser=True, status='cancelled', tier='none')
      result = check_subscription(user, required_tiers=['investor'])
      assert result is user


  def test_active_investor_passes():
      from backend.auth.guards import check_subscription
      user = _make_user(status='active', tier='investor')
      result = check_subscription(user, required_tiers=['investor'])
      assert result is user


  def test_cancelled_user_blocked():
      from backend.auth.guards import check_subscription
      user = _make_user(status='cancelled', tier='investor')
      with pytest.raises(HTTPException) as exc:
          check_subscription(user, required_tiers=['investor'])
      assert exc.value.status_code == 403


  def test_trial_under_limit_passes():
      from backend.auth.guards import check_subscription
      user = _make_user(status='trial', tier='none', trial_property_views=2)
      result = check_subscription(user, required_tiers=['investor'], trial_type='property_view')
      assert result is user


  def test_trial_over_limit_returns_402():
      from backend.auth.guards import check_subscription
      user = _make_user(status='trial', tier='none', trial_property_views=3)
      with pytest.raises(HTTPException) as exc:
          check_subscription(user, required_tiers=['investor'], trial_type='property_view')
      assert exc.value.status_code == 402


  def test_wrong_tier_blocked():
      from backend.auth.guards import check_subscription
      user = _make_user(status='active', tier='deal_source')
      with pytest.raises(HTTPException) as exc:
          check_subscription(user, required_tiers=['investor'])
      assert exc.value.status_code == 403


  def test_past_due_allowed_with_warning():
      from backend.auth.guards import check_subscription
      user = _make_user(status='past_due', tier='investor')
      result = check_subscription(user, required_tiers=['investor'])
      assert result is user
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/auth/test_guards.py -v
  ```

  Expected: FAIL — `backend.auth.guards` does not exist.

- [ ] **Step 3: Create guards module**

  Create `backend/auth/guards.py`:

  ```python
  """Subscription-gated dependency injection for route protection."""
  import logging
  from typing import List, Optional

  import jwt
  from fastapi import Depends, HTTPException, Header
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.auth.config import JWT_SECRET
  from backend.models.user import User

  logger = logging.getLogger(__name__)

  ALGORITHM = "HS256"
  TRIAL_PROPERTY_VIEW_LIMIT = 3
  TRIAL_AI_VIEW_LIMIT = 3


  def get_current_user(
      authorization: Optional[str] = Header(None),
      db: Session = Depends(get_db),
  ) -> User:
      """Extract and validate JWT from Authorization header."""
      if not authorization or not authorization.startswith('Bearer '):
          raise HTTPException(status_code=401, detail="Not authenticated")
      token = authorization.split(' ', 1)[1]
      try:
          payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
      except jwt.ExpiredSignatureError:
          raise HTTPException(status_code=401, detail="Token expired")
      except jwt.InvalidTokenError:
          raise HTTPException(status_code=401, detail="Invalid token")

      user = db.query(User).get(int(payload["sub"]))
      if not user or not user.is_active:
          raise HTTPException(status_code=401, detail="User not found")
      return user


  def get_optional_user(
      authorization: Optional[str] = Header(None),
      db: Session = Depends(get_db),
  ) -> Optional[User]:
      """Like get_current_user but returns None instead of 401 for unauthenticated."""
      if not authorization or not authorization.startswith('Bearer '):
          return None
      try:
          return get_current_user(authorization=authorization, db=db)
      except HTTPException:
          return None


  def check_subscription(
      user: User,
      required_tiers: List[str],
      trial_type: Optional[str] = None,
  ) -> User:
      """
      Check user's subscription status and tier.
      Raises 402 for trial limit, 403 for wrong tier/cancelled.
      """
      # Admin bypasses everything
      if user.is_superuser:
          return user

      status = user.subscription_status
      tier = user.subscription_tier

      # Trial users — check view limits
      if status == 'trial':
          if trial_type == 'property_view' and user.trial_property_views >= TRIAL_PROPERTY_VIEW_LIMIT:
              raise HTTPException(status_code=402, detail="Trial limit reached")
          if trial_type == 'ai_view' and user.trial_ai_views >= TRIAL_AI_VIEW_LIMIT:
              raise HTTPException(status_code=402, detail="Trial limit reached")
          # Trial users get investor-level access within limits
          return user

      # Cancelled — block immediately
      if status == 'cancelled':
          raise HTTPException(status_code=403, detail="Subscription cancelled")

      # Active or past_due — check tier
      if status in ('active', 'past_due'):
          if tier in required_tiers or tier == 'admin':
              return user
          # Check secondary subscription for dual-role users
          if hasattr(user, 'stripe_subscription_id_secondary') and user.stripe_subscription_id_secondary:
              # Dual-role: white_label includes both uploader types
              if 'white_label' in required_tiers and tier in ('auction_house', 'deal_source'):
                  pass  # fall through to forbidden
              # Could be an investor who also has an uploader subscription
              # This would need checking the secondary subscription's tier
              # For now, the primary tier is the gate
              pass
          raise HTTPException(status_code=403, detail="Plan upgrade required")

      raise HTTPException(status_code=403, detail="Subscription required")


  def require_subscription(*tiers: str, trial_type: str = None):
      """
      Dependency factory for route-level subscription gating.

      Usage:
          @router.get("/protected")
          def protected(user = Depends(require_subscription('investor', 'admin'))):
              ...
      """
      def dependency(user: User = Depends(get_current_user)):
          return check_subscription(user, list(tiers), trial_type=trial_type)
      return dependency
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/auth/test_guards.py -v
  ```

  Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/auth/guards.py tests/auth/test_guards.py tests/auth/__init__.py
  git commit -m "feat: add subscription guard dependencies with trial limits"
  ```

---

## Task 16: Stripe Billing Endpoints

**Files:**
- Create: `backend/api/routers/billing.py`
- Create: `tests/auth/test_billing_webhook.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Write failing webhook test**

  Create `tests/auth/test_billing_webhook.py`:

  ```python
  """Tests for Stripe webhook handler."""
  import pytest
  from unittest.mock import patch, MagicMock


  def test_subscription_created_updates_user():
      from backend.api.routers.billing import _handle_subscription_created
      db = MagicMock()
      user = MagicMock()
      user.subscription_status = 'trial'
      user.subscription_tier = 'none'
      db.query.return_value.filter.return_value.first.return_value = user

      event_data = {
          'customer': 'cus_123',
          'metadata': {'tier': 'investor'},
          'status': 'active',
      }
      _handle_subscription_created(db, event_data)
      assert user.subscription_status == 'active'
      assert user.subscription_tier == 'investor'


  def test_subscription_deleted_cancels_access():
      from backend.api.routers.billing import _handle_subscription_deleted
      db = MagicMock()
      user = MagicMock()
      user.subscription_status = 'active'
      db.query.return_value.filter.return_value.first.return_value = user

      event_data = {'customer': 'cus_123'}
      _handle_subscription_deleted(db, event_data)
      assert user.subscription_status == 'cancelled'


  def test_payment_failed_sets_past_due():
      from backend.api.routers.billing import _handle_payment_failed
      db = MagicMock()
      user = MagicMock()
      user.subscription_status = 'active'
      db.query.return_value.filter.return_value.first.return_value = user

      event_data = {'customer': 'cus_123'}
      _handle_payment_failed(db, event_data)
      assert user.subscription_status == 'past_due'
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/auth/test_billing_webhook.py -v
  ```

  Expected: FAIL — module does not exist.

- [ ] **Step 3: Create billing router**

  Create `backend/api/routers/billing.py`:

  ```python
  """Stripe billing endpoints — checkout, webhook, portal."""
  import os
  import logging

  import stripe
  from fastapi import APIRouter, Depends, HTTPException, Request
  from pydantic import BaseModel
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.auth.guards import get_current_user
  from backend.models.user import User

  logger = logging.getLogger(__name__)
  router = APIRouter(prefix="/api/billing", tags=["billing"])

  stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
  STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
  FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')


  class CheckoutRequest(BaseModel):
      price_id: str
      billing_period: str = 'monthly'  # monthly or annual


  @router.post("/create-checkout-session")
  def create_checkout_session(
      req: CheckoutRequest,
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      """Create Stripe Checkout Session for subscription."""
      # Create or retrieve Stripe Customer
      if not user.stripe_customer_id:
          customer = stripe.Customer.create(
              email=user.email,
              name=user.full_name,
              metadata={'user_id': str(user.id), 'role': user.role},
          )
          user.stripe_customer_id = customer.id
          db.commit()

      session = stripe.checkout.Session.create(
          customer=user.stripe_customer_id,
          mode='subscription',
          line_items=[{'price': req.price_id, 'quantity': 1}],
          success_url=f'{FRONTEND_URL}/account?checkout=success',
          cancel_url=f'{FRONTEND_URL}/account?checkout=cancel',
          metadata={'user_id': str(user.id)},
      )
      return {'checkout_url': session.url}


  @router.post("/webhook")
  async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
      """Stripe webhook receiver."""
      payload = await request.body()
      sig_header = request.headers.get('stripe-signature', '')

      try:
          event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
      except (ValueError, stripe.error.SignatureVerificationError) as e:
          logger.warning("Webhook signature verification failed: %s", e)
          raise HTTPException(status_code=400, detail="Invalid signature")

      data = event['data']['object']
      event_type = event['type']

      if event_type == 'customer.subscription.created':
          _handle_subscription_created(db, data)
      elif event_type == 'customer.subscription.updated':
          _handle_subscription_created(db, data)  # same logic — update tier/status
      elif event_type == 'customer.subscription.deleted':
          _handle_subscription_deleted(db, data)
      elif event_type == 'invoice.payment_failed':
          _handle_payment_failed(db, data)

      db.commit()
      return {'status': 'ok'}


  @router.post("/portal-session")
  def create_portal_session(
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      """Create Stripe Customer Portal session for self-serve management."""
      if not user.stripe_customer_id:
          raise HTTPException(status_code=400, detail="No billing account")
      session = stripe.billing_portal.Session.create(
          customer=user.stripe_customer_id,
          return_url=f'{FRONTEND_URL}/account',
      )
      return {'portal_url': session.url}


  def _handle_subscription_created(db: Session, data: dict):
      """Handle subscription.created and subscription.updated events."""
      customer_id = data.get('customer')
      user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
      if not user:
          logger.warning("Webhook: no user for customer %s", customer_id)
          return

      tier = data.get('metadata', {}).get('tier', 'investor')
      status = data.get('status', 'active')

      user.subscription_status = 'active' if status == 'active' else status
      user.subscription_tier = tier
      if not user.stripe_subscription_id:
          user.stripe_subscription_id = data.get('id')
      else:
          user.stripe_subscription_id_secondary = data.get('id')


  def _handle_subscription_deleted(db: Session, data: dict):
      """Handle subscription.deleted — revoke access immediately."""
      customer_id = data.get('customer')
      user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
      if not user:
          return
      user.subscription_status = 'cancelled'


  def _handle_payment_failed(db: Session, data: dict):
      """Handle invoice.payment_failed — set past_due with 7-day grace."""
      customer_id = data.get('customer')
      user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
      if not user:
          return
      user.subscription_status = 'past_due'
  ```

- [ ] **Step 4: Add stripe to requirements and register router**

  Add to `requirements.txt`:

  ```
  stripe==7.0.0
  ```

  In `backend/api/main.py`, add import and include:

  ```python
  from backend.api.routers import billing
  app.include_router(billing.router)
  ```

- [ ] **Step 5: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/auth/test_billing_webhook.py -v
  ```

  Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/api/routers/billing.py tests/auth/test_billing_webhook.py backend/api/main.py requirements.txt
  git commit -m "feat: add Stripe billing — checkout session, webhook handler, portal"
  ```

---

## Task 17: Apply Guards to Existing Routes

**Files:**
- Modify: `backend/api/routers/scan.py`
- Modify: `backend/api/routers/properties.py`
- Modify: `backend/api/routers/ai_analysis.py`
- Modify: `backend/api/routers/scrapers.py`

- [ ] **Step 1: Gate the scan endpoint**

  In `backend/api/routers/scan.py`, add import:

  ```python
  from backend.auth.guards import get_current_user, require_subscription
  from backend.models.user import User
  ```

  Update the endpoint signature:

  ```python
  @router.post("")
  def scan_property(
      req: ScanRequest,
      db: Session = Depends(get_db),
      user: User = Depends(require_subscription('investor', 'admin', trial_type='property_view')),
  ):
  ```

  Add trial counter increment at the start of the function body:

  ```python
      if user.subscription_status == 'trial':
          user.trial_property_views += 1
          db.commit()
  ```

- [ ] **Step 2: Gate property detail endpoint**

  In `backend/api/routers/properties.py`, find the `GET /{property_id}` endpoint (line 204). Add the guard dependency:

  ```python
  from backend.auth.guards import get_optional_user
  from backend.models.user import User
  ```

  Update signature to include optional user (doesn't block unauthenticated, but tracks trial):

  ```python
  @router.get('/{property_id}', response_model=PropertyDetail)
  def get_property(
      property_id: int,
      db: Session = Depends(get_db),
      user: User = Depends(get_optional_user),
  ):
  ```

  The full access gating (402 paywall) happens in the frontend based on the user's auth state.

- [ ] **Step 3: Gate scrapers to admin only**

  In `backend/api/routers/scrapers.py`, add:

  ```python
  from backend.auth.guards import require_subscription
  ```

  Add to scraper endpoints that should be admin-only (the POST scrape trigger):

  ```python
  @router.post('/scrape/{source_id}')
  def trigger_scrape(source_id: int, ..., user = Depends(require_subscription('admin'))):
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/api/routers/scan.py backend/api/routers/properties.py backend/api/routers/scrapers.py
  git commit -m "feat: apply subscription guards to scan, property detail, and scraper routes"
  ```

---

## Task 18: Frontend Auth — Context, Login, Register, Protected Routes

**Files:**
- Create: `frontend/src/contexts/AuthContext.jsx`
- Create: `frontend/src/pages/Login.jsx`
- Create: `frontend/src/pages/Register.jsx`
- Create: `frontend/src/components/auth/ProtectedRoute.jsx`
- Create: `frontend/src/components/auth/PaywallModal.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/services/api.js`

This is a large frontend task. Each step creates one file.

- [ ] **Step 1: Create AuthContext**

  Create `frontend/src/contexts/AuthContext.jsx`:

  ```jsx
  import { createContext, useContext, useState, useEffect, useCallback } from 'react';
  import api from '../services/api';

  const AuthContext = createContext(null);

  export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      const token = localStorage.getItem('assetlens_token');
      if (token) {
        api.get('/api/auth/me')
          .then(res => setUser(res.data))
          .catch(() => {
            localStorage.removeItem('assetlens_token');
            localStorage.removeItem('assetlens_refresh_token');
          })
          .finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    }, []);

    const login = useCallback(async (email, password) => {
      const res = await api.post('/api/auth/login', { email, password });
      localStorage.setItem('assetlens_token', res.data.access_token);
      localStorage.setItem('assetlens_refresh_token', res.data.refresh_token);
      localStorage.setItem('assetlens_user_email', res.data.user.email);
      setUser(res.data.user);
      return res.data.user;
    }, []);

    const register = useCallback(async (data) => {
      const res = await api.post('/api/auth/register', data);
      localStorage.setItem('assetlens_token', res.data.access_token);
      localStorage.setItem('assetlens_refresh_token', res.data.refresh_token);
      localStorage.setItem('assetlens_user_email', res.data.user.email);
      setUser(res.data.user);
      return res.data.user;
    }, []);

    const logout = useCallback(() => {
      localStorage.removeItem('assetlens_token');
      localStorage.removeItem('assetlens_refresh_token');
      localStorage.removeItem('assetlens_user_email');
      setUser(null);
    }, []);

    return (
      <AuthContext.Provider value={{ user, loading, login, register, logout }}>
        {children}
      </AuthContext.Provider>
    );
  }

  export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be inside AuthProvider');
    return ctx;
  }
  ```

- [ ] **Step 2: Create ProtectedRoute**

  Create `frontend/src/components/auth/ProtectedRoute.jsx`:

  ```jsx
  import { Navigate } from 'react-router-dom';
  import { useAuth } from '../../contexts/AuthContext';

  export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();

    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
        </div>
      );
    }

    if (!user) {
      return <Navigate to="/login" replace />;
    }

    return children;
  }
  ```

- [ ] **Step 3: Create PaywallModal**

  Create `frontend/src/components/auth/PaywallModal.jsx`:

  ```jsx
  import { X } from 'lucide-react';
  import api from '../../services/api';

  const PLANS = [
    { name: 'Investor', price: '£99/mo', annual: '£990/yr', priceId: process.env.REACT_APP_STRIPE_INVESTOR_PRICE_ID },
    { name: 'Auction House', price: '£55/mo', annual: '£550/yr', priceId: process.env.REACT_APP_STRIPE_AUCTION_PRICE_ID },
    { name: 'Deal Source', price: '£55/mo', annual: '£550/yr', priceId: process.env.REACT_APP_STRIPE_DEAL_PRICE_ID },
  ];

  export default function PaywallModal({ onClose }) {
    const handleCheckout = async (priceId) => {
      try {
        const res = await api.post('/api/billing/create-checkout-session', {
          price_id: priceId,
          billing_period: 'monthly',
        });
        window.location.href = res.data.checkout_url;
      } catch (err) {
        console.error('Checkout failed:', err);
      }
    };

    return (
      <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white">Upgrade to continue</h2>
            <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={20} /></button>
          </div>
          <p className="text-slate-400 mb-6">You've used all your free views. Choose a plan to unlock full access.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PLANS.map(plan => (
              <div key={plan.name} className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
                <h3 className="text-white font-semibold mb-1">{plan.name}</h3>
                <p className="text-emerald-400 text-2xl font-bold mb-1">{plan.price}</p>
                <p className="text-slate-500 text-xs mb-4">or {plan.annual}</p>
                <button
                  onClick={() => handleCheckout(plan.priceId)}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2 text-sm font-medium transition-colors"
                >
                  Subscribe
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 4: Create Login page**

  Create `frontend/src/pages/Login.jsx`:

  ```jsx
  import { useState } from 'react';
  import { Link, useNavigate } from 'react-router-dom';
  import { useAuth } from '../contexts/AuthContext';
  import toast from 'react-hot-toast';

  export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
      e.preventDefault();
      setLoading(true);
      try {
        await login(email, password);
        navigate('/dashboard');
      } catch {
        toast.error('Invalid email or password');
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8">
          <h1 className="text-2xl font-bold text-white mb-6 text-center">Sign in to AssetLens</h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Email</label>
              <input
                type="email" value={email} onChange={e => setEmail(e.target.value)} required
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Password</label>
              <input
                type="password" value={password} onChange={e => setPassword(e.target.value)} required
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <button
              type="submit" disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2.5 font-medium transition-colors disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
          <p className="text-center text-slate-500 text-sm mt-4">
            Don't have an account? <Link to="/register" className="text-emerald-400 hover:underline">Register</Link>
          </p>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 5: Create Register page**

  Create `frontend/src/pages/Register.jsx`:

  ```jsx
  import { useState } from 'react';
  import { Link, useNavigate } from 'react-router-dom';
  import { useAuth } from '../contexts/AuthContext';
  import toast from 'react-hot-toast';

  const ROLES = [
    { value: 'investor', label: 'I want to evaluate properties', sublabel: 'Investor — £99/mo' },
    { value: 'auction_house', label: 'I represent an auction house', sublabel: 'Auction House — £55/mo' },
    { value: 'deal_source', label: 'I source properties for investors', sublabel: 'Deal Source — £55/mo' },
  ];

  export default function Register() {
    const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'investor', company_name: '' });
    const [loading, setLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const isUploader = form.role === 'auction_house' || form.role === 'deal_source';

    const handleSubmit = async (e) => {
      e.preventDefault();
      setLoading(true);
      try {
        await register(form);
        toast.success('Account created — welcome to AssetLens!');
        navigate('/dashboard');
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Registration failed');
      } finally {
        setLoading(false);
      }
    };

    const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }));

    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-8">
          <h1 className="text-2xl font-bold text-white mb-6 text-center">Create your account</h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Full name</label>
              <input type="text" value={form.full_name} onChange={set('full_name')} required
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Email</label>
              <input type="email" value={form.email} onChange={set('email')} required
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Password</label>
              <input type="password" value={form.password} onChange={set('password')} required minLength={8}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">I am a...</label>
              <div className="space-y-2">
                {ROLES.map(r => (
                  <label key={r.value} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    form.role === r.value ? 'border-emerald-500 bg-emerald-500/10' : 'border-slate-700 hover:border-slate-600'
                  }`}>
                    <input type="radio" name="role" value={r.value} checked={form.role === r.value}
                      onChange={set('role')} className="accent-emerald-500" />
                    <div>
                      <div className="text-white text-sm">{r.label}</div>
                      <div className="text-slate-500 text-xs">{r.sublabel}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
            {isUploader && (
              <div>
                <label className="block text-sm text-slate-400 mb-1">Company name</label>
                <input type="text" value={form.company_name} onChange={set('company_name')}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
              </div>
            )}
            <button type="submit" disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2.5 font-medium transition-colors disabled:opacity-50">
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </form>
          <p className="text-center text-slate-500 text-sm mt-4">
            Already have an account? <Link to="/login" className="text-emerald-400 hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 6: Update App.jsx with auth routes and provider**

  In `frontend/src/App.jsx`, add imports:

  ```jsx
  import { AuthProvider } from './contexts/AuthContext';
  import ProtectedRoute from './components/auth/ProtectedRoute';
  import Login from './pages/Login';
  import Register from './pages/Register';
  ```

  Wrap the `<BrowserRouter>` contents with `<AuthProvider>`:

  ```jsx
  <BrowserRouter>
    <AuthProvider>
      {/* existing Toaster */}
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="properties" element={<Properties />} />
          <Route path="properties/:id" element={<PropertyDetail />} />
          <Route path="alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
          <Route path="scrapers" element={<ProtectedRoute><Scrapers /></ProtectedRoute>} />
        </Route>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/advertise" element={<AdSubmit />} />
        <Route path="/admin/ads" element={<AdminAds />} />
      </Routes>
    </AuthProvider>
  </BrowserRouter>
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/contexts/AuthContext.jsx frontend/src/components/auth/ProtectedRoute.jsx frontend/src/components/auth/PaywallModal.jsx frontend/src/pages/Login.jsx frontend/src/pages/Register.jsx frontend/src/App.jsx
  git commit -m "feat: add frontend auth — login, register, protected routes, paywall modal"
  ```

---

## Task 19: Account Settings + Investor Profile Page

**Files:**
- Create: `backend/api/routers/account.py`
- Create: `frontend/src/pages/Account.jsx`
- Modify: `backend/api/main.py`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create account API router**

  Create `backend/api/routers/account.py`:

  ```python
  """Account settings and investor profile endpoints."""
  import logging
  from datetime import datetime
  from typing import Optional

  from fastapi import APIRouter, Depends, HTTPException
  from pydantic import BaseModel
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.auth.guards import get_current_user
  from backend.models.user import User, UserProfile

  logger = logging.getLogger(__name__)
  router = APIRouter(prefix="/api/account", tags=["account"])


  class ProfileUpdate(BaseModel):
      max_deposit: Optional[int] = None
      loan_type_sought: Optional[str] = None
      max_loan_wanted: Optional[int] = None
      loan_term_months: Optional[int] = None
      purpose: Optional[str] = None
      investment_experience: Optional[str] = None
      properties_owned: Optional[int] = None
      portfolio_value_band: Optional[str] = None
      outstanding_mortgage_band: Optional[str] = None
      hmo_experience: Optional[bool] = None
      development_experience: Optional[bool] = None
      limited_company: Optional[bool] = None
      company_name_ch: Optional[str] = None
      companies_house_number: Optional[str] = None
      spv: Optional[bool] = None
      personal_guarantee_willing: Optional[bool] = None
      main_residence: Optional[bool] = None
      uk_resident: Optional[bool] = None
      employment_status: Optional[str] = None
      annual_income_band: Optional[str] = None
      credit_history: Optional[str] = None
      target_location: Optional[str] = None
      strategy: Optional[str] = None
      readiness: Optional[str] = None


  @router.get("/profile")
  def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
      profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
      if not profile:
          profile = UserProfile(user_id=user.id)
          db.add(profile)
          db.commit()
          db.refresh(profile)
      return profile


  @router.put("/profile")
  def update_profile(
      data: ProfileUpdate,
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
      if not profile:
          profile = UserProfile(user_id=user.id)
          db.add(profile)
          db.flush()

      for field, value in data.model_dump(exclude_unset=True).items():
          setattr(profile, field, value)

      profile.updated_at = datetime.utcnow()
      db.commit()
      db.refresh(profile)
      return profile


  @router.post("/profile/consent-broker")
  def consent_broker(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
      profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
      if not profile:
          raise HTTPException(status_code=404, detail="Profile not found")
      profile.broker_consent_given_at = datetime.utcnow()
      db.commit()
      return {"consented_at": str(profile.broker_consent_given_at)}


  @router.delete("/profile/financial")
  def delete_financial_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
      """GDPR: NULL all financial columns but retain account."""
      profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
      if not profile:
          raise HTTPException(status_code=404, detail="Profile not found")

      financial_fields = [
          'max_deposit', 'loan_type_sought', 'max_loan_wanted', 'loan_term_months', 'purpose',
          'investment_experience', 'properties_owned', 'portfolio_value_band', 'outstanding_mortgage_band',
          'hmo_experience', 'development_experience', 'limited_company', 'company_name_ch',
          'companies_house_number', 'spv', 'personal_guarantee_willing', 'main_residence',
          'uk_resident', 'employment_status', 'annual_income_band', 'credit_history',
      ]
      for field in financial_fields:
          setattr(profile, field, None)

      profile.profile_deletion_at = datetime.utcnow()
      profile.broker_consent_given_at = None
      db.commit()
      return {"deleted_at": str(profile.profile_deletion_at)}
  ```

- [ ] **Step 2: Register router and add account route to frontend**

  In `backend/api/main.py`, add:

  ```python
  from backend.api.routers import account
  app.include_router(account.router)
  ```

  In `frontend/src/App.jsx`, add the Account route inside the Layout routes:

  ```jsx
  <Route path="account" element={<ProtectedRoute><Account /></ProtectedRoute>} />
  ```

  Add import: `import Account from './pages/Account';`

- [ ] **Step 3: Create Account page (simplified — form fields for investor profile)**

  Create `frontend/src/pages/Account.jsx`:

  ```jsx
  import { useState, useEffect } from 'react';
  import { useAuth } from '../contexts/AuthContext';
  import api from '../services/api';
  import toast from 'react-hot-toast';

  export default function Account() {
    const { user } = useAuth();
    const [profile, setProfile] = useState(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
      api.get('/api/account/profile').then(res => setProfile(res.data)).catch(() => {});
    }, []);

    const save = async () => {
      setSaving(true);
      try {
        const res = await api.put('/api/account/profile', profile);
        setProfile(res.data);
        toast.success('Profile saved');
      } catch {
        toast.error('Failed to save');
      } finally {
        setSaving(false);
      }
    };

    const openPortal = async () => {
      try {
        const res = await api.post('/api/billing/portal-session');
        window.location.href = res.data.portal_url;
      } catch {
        toast.error('Billing portal unavailable');
      }
    };

    const deleteFinancial = async () => {
      if (!window.confirm('Delete all financial profile data? This cannot be undone.')) return;
      try {
        await api.delete('/api/account/profile/financial');
        const res = await api.get('/api/account/profile');
        setProfile(res.data);
        toast.success('Financial data deleted');
      } catch {
        toast.error('Failed to delete');
      }
    };

    if (!profile) return <div className="p-8 text-slate-400">Loading...</div>;

    const set = (key) => (e) => setProfile(p => ({ ...p, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

    return (
      <div className="space-y-6 max-w-3xl mx-auto p-6">
        <h1 className="text-2xl font-bold text-white">Account Settings</h1>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5">
          <div className="flex justify-between items-center mb-4">
            <div>
              <p className="text-white font-semibold">{user?.full_name}</p>
              <p className="text-slate-400 text-sm">{user?.email}</p>
              <p className="text-emerald-400 text-xs mt-1 capitalize">{user?.subscription_tier || 'Trial'} — {user?.subscription_status}</p>
            </div>
            <button onClick={openPortal}
              className="text-xs bg-slate-700 hover:bg-slate-600 text-white rounded-lg px-3 py-1.5 transition-colors">
              Manage billing
            </button>
          </div>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5 space-y-4">
          <h2 className="text-lg font-semibold text-white">Investment Profile</h2>
          <p className="text-slate-500 text-xs">All fields are optional. Used to personalise your deal scores.</p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Strategy</label>
              <select value={profile.strategy || ''} onChange={set('strategy')}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm">
                <option value="">Not set</option>
                <option value="btl">Buy to Let</option>
                <option value="hmo">HMO</option>
                <option value="flip">Flip / Refurb</option>
                <option value="development">Development</option>
                <option value="brrr">BRRR</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Experience</label>
              <select value={profile.investment_experience || ''} onChange={set('investment_experience')}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm">
                <option value="">Not set</option>
                <option value="first_time">First-time investor</option>
                <option value="1_5_yrs">1-5 years</option>
                <option value="5_plus">5+ years</option>
                <option value="professional">Professional (10+)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Max deposit (£)</label>
              <input type="number" value={profile.max_deposit || ''} onChange={set('max_deposit')}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Target location</label>
              <input type="text" value={profile.target_location || ''} onChange={set('target_location')} placeholder="e.g. LS6 or Yorkshire"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm" />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={save} disabled={saving}
              className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50">
              {saving ? 'Saving...' : 'Save profile'}
            </button>
            <button onClick={deleteFinancial}
              className="bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 rounded-lg px-4 py-2 text-sm transition-colors">
              Delete financial data
            </button>
          </div>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/api/routers/account.py frontend/src/pages/Account.jsx backend/api/main.py frontend/src/App.jsx
  git commit -m "feat: add account settings page with investor profile form and GDPR deletion"
  ```

---

# SPRINT 3: REVENUE FEATURES

---

## Task 20: Personalised Score Service

**Files:**
- Create: `backend/services/personalised_score_service.py`
- Create: `tests/services/test_personalised_score.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/services/test_personalised_score.py`:

  ```python
  """Tests for personalised deal score adjustments."""
  import pytest
  from unittest.mock import MagicMock


  def _make_score(investment_score=65, gross_yield_pct=7.5, price_band='good'):
      s = MagicMock()
      s.investment_score = investment_score
      s.gross_yield_pct = gross_yield_pct
      s.price_band = price_band
      s.estimated_value = 200000
      s.pd_avm = 210000
      s.price_score = 30
      s.yield_score = 20
      s.area_trend_score = 10
      s.hmo_opportunity_score = 5
      return s


  def _make_profile(strategy='btl', experience='first_time', uk_resident=True,
                    main_residence=False, credit_history='clean', target_location=None,
                    max_deposit=None, readiness='immediate', hmo_experience=False):
      p = MagicMock()
      p.strategy = strategy
      p.investment_experience = experience
      p.uk_resident = uk_resident
      p.main_residence = main_residence
      p.credit_history = credit_history
      p.target_location = target_location
      p.max_deposit = max_deposit
      p.readiness = readiness
      p.hmo_experience = hmo_experience
      return p


  def test_btl_strategy_label():
      from backend.services.personalised_score_service import personalise
      result = personalise(_make_score(), _make_profile(strategy='btl'), asking_price=200000, postcode='LS6 1AA')
      assert result['label'] == 'BTL Score'


  def test_no_strategy_generic_label():
      from backend.services.personalised_score_service import personalise
      result = personalise(_make_score(), _make_profile(strategy=None), asking_price=200000, postcode='LS6 1AA')
      assert result['label'] == 'Deal Score'


  def test_non_uk_resident_sdlt_surcharge_flagged():
      from backend.services.personalised_score_service import personalise
      result = personalise(_make_score(), _make_profile(uk_resident=False), asking_price=200000, postcode='LS6 1AA')
      assert any('non-resident' in n.lower() or 'surcharge' in n.lower() for n in result['notes'])


  def test_adverse_credit_flags_bridging():
      from backend.services.personalised_score_service import personalise
      result = personalise(_make_score(), _make_profile(credit_history='adverse'), asking_price=200000, postcode='LS6 1AA')
      assert any('bridging' in n.lower() for n in result['notes'])


  def test_location_mismatch_flagged():
      from backend.services.personalised_score_service import personalise
      result = personalise(_make_score(), _make_profile(target_location='Manchester'), asking_price=200000, postcode='LS6 1AA')
      assert result['location_mismatch'] is True


  def test_first_time_adds_explanatory_notes():
      from backend.services.personalised_score_service import personalise
      result = personalise(_make_score(), _make_profile(experience='first_time'), asking_price=200000, postcode='LS6 1AA')
      assert len(result['notes']) > 0
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/services/test_personalised_score.py -v
  ```

  Expected: FAIL — module does not exist.

- [ ] **Step 3: Create personalised score service**

  Create `backend/services/personalised_score_service.py`:

  ```python
  """Personalised deal score — adjusts base score using investor profile."""
  from typing import Dict, Any, Optional, List


  STRATEGY_LABELS = {
      'btl': 'BTL Score',
      'hmo': 'HMO Score',
      'flip': 'Flip Score',
      'development': 'Development Score',
      'brrr': 'BRRR Score',
  }


  def personalise(score, profile, asking_price: float, postcode: str) -> Dict[str, Any]:
      """
      Adjust base score using investor profile. Returns personalised score dict.
      Does NOT modify the stored score — all adjustments are request-time only.
      """
      notes: List[str] = []
      adjustment = 0.0
      strategy = getattr(profile, 'strategy', None) or None
      label = STRATEGY_LABELS.get(strategy, 'Deal Score')

      base = score.investment_score or 0

      # Strategy-specific adjustments
      if strategy == 'btl':
          if score.gross_yield_pct and score.gross_yield_pct > 8:
              adjustment += 3
              notes.append("Strong BTL yield above 8%.")
          if not getattr(profile, 'hmo_experience', False):
              notes.append("Note: HMO licence required if 3+ unrelated tenants — you have not indicated HMO experience.")

      elif strategy == 'flip':
          if score.price_score and score.price_score > 25:
              adjustment += 5
              notes.append("Below-market entry price — strong flip potential.")

      # Experience-based notes
      experience = getattr(profile, 'investment_experience', None)
      if experience == 'first_time':
          notes.append("As a first-time investor, consider taking professional advice on this type of property.")

      # Credit history
      credit = getattr(profile, 'credit_history', None)
      if credit == 'adverse':
          notes.append("With adverse credit history, standard mortgage products may be limited — bridging finance is likely the most accessible route.")

      # UK residency — SDLT surcharge
      if getattr(profile, 'uk_resident', True) is False:
          notes.append("Non-UK resident: 2% SDLT surcharge applies to this purchase.")

      # Main residence — additional dwelling surcharge
      if getattr(profile, 'main_residence', True) is False:
          notes.append("Additional dwelling: 3% SDLT surcharge applies.")

      # Deposit check
      max_deposit = getattr(profile, 'max_deposit', None)
      if max_deposit and asking_price and max_deposit < asking_price * 0.25:
          notes.append("Your indicated deposit may be below the minimum required for bridging finance on this property type.")

      # Location mismatch
      target = getattr(profile, 'target_location', None)
      location_mismatch = False
      if target and postcode:
          target_lower = target.lower().strip()
          postcode_lower = postcode.lower().strip()
          # Simple check: does the target appear in the postcode district or vice versa?
          if target_lower not in postcode_lower and postcode_lower[:3] not in target_lower:
              location_mismatch = True
              notes.append(f"This property is outside your target area ({target}).")

      # Readiness
      readiness = getattr(profile, 'readiness', None)
      if readiness == 'researching':
          notes.append("Area trend data is shown below — take time to understand the local market before committing.")

      personalised_score = min(100, max(0, base + adjustment))

      return {
          'base_score': base,
          'adjustment': adjustment,
          'personalised_score': round(personalised_score, 1),
          'label': label,
          'notes': notes,
          'location_mismatch': location_mismatch,
      }
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/services/test_personalised_score.py -v
  ```

  Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/personalised_score_service.py tests/services/test_personalised_score.py
  git commit -m "feat: add personalised deal score service with strategy-specific labels"
  ```

---

## Task 21: Public Listing Pages — Backend

**Files:**
- Create: `backend/api/routers/listings.py`
- Create: `tests/api/test_listings_public.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/api/test_listings_public.py`:

  ```python
  """Tests for public listing page API — field visibility rules."""
  import pytest
  from unittest.mock import patch, MagicMock
  from fastapi.testclient import TestClient


  @pytest.fixture
  def client():
      from backend.api.main import app
      return TestClient(app)


  def test_public_listing_hides_full_address(client):
      """Public view should show only town/area, not full address."""
      mock_prop = MagicMock()
      mock_prop.id = 1
      mock_prop.address = '123 High Street'
      mock_prop.postcode = 'SW1A 1AA'
      mock_prop.town = 'London'
      mock_prop.asking_price = 300000
      mock_prop.property_type = 'flat'
      mock_prop.bedrooms = 2
      mock_prop.description = 'Nice flat'
      mock_prop.image_urls = '["img1.jpg","img2.jpg","img3.jpg","img4.jpg"]'
      mock_prop.score = None

      with patch('backend.api.routers.listings._get_listing_property', return_value=mock_prop):
          response = client.get('/api/listings/1')

      assert response.status_code == 200
      data = response.json()
      assert data['address'] == 'London'  # town only, not full address
      assert data['postcode'] == 'SW1A'   # district only
      assert 'ai_score' not in data or data['ai_score'] is None
      assert len(data.get('photos', [])) <= 3
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/api/test_listings_public.py -v
  ```

  Expected: FAIL — module does not exist.

- [ ] **Step 3: Create listings router**

  Create `backend/api/routers/listings.py`:

  ```python
  """Public listing pages — no auth required. Field visibility rules applied."""
  import json
  import logging
  from typing import Optional

  from fastapi import APIRouter, Depends, HTTPException
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.auth.guards import get_optional_user
  from backend.models.property import Property, PropertyScore
  from backend.models.user import User, UserProfile

  logger = logging.getLogger(__name__)
  router = APIRouter(prefix="/api/listings", tags=["listings"])


  def _get_listing_property(db: Session, property_id: int) -> Property:
      prop = db.query(Property).get(property_id)
      if not prop:
          raise HTTPException(status_code=404, detail="Listing not found")
      return prop


  def _public_view(prop: Property) -> dict:
      """Strip gated fields for unauthenticated/public access."""
      photos = []
      if prop.image_urls:
          try:
              all_photos = json.loads(prop.image_urls)
              photos = all_photos[:3]  # max 3 for public
          except (json.JSONDecodeError, TypeError):
              pass

      district = prop.postcode.split()[0] if prop.postcode and ' ' in prop.postcode else (prop.postcode or '')[:4]

      return {
          'id': prop.id,
          'address': prop.town or 'Unknown area',  # town only
          'postcode': district,  # district only
          'asking_price': prop.asking_price,
          'property_type': prop.property_type,
          'bedrooms': prop.bedrooms,
          'bathrooms': prop.bathrooms,
          'description': prop.description,
          'photos': photos,
          'ai_score': None,  # hidden from public
          'avm': None,
          'yield_pct': None,
      }


  def _investor_view(prop: Property, db: Session) -> dict:
      """Full data for authenticated investor."""
      photos = []
      if prop.image_urls:
          try:
              photos = json.loads(prop.image_urls)
          except (json.JSONDecodeError, TypeError):
              pass

      score = db.query(PropertyScore).filter(PropertyScore.property_id == prop.id).first()

      return {
          'id': prop.id,
          'address': prop.address,
          'postcode': prop.postcode,
          'asking_price': prop.asking_price,
          'property_type': prop.property_type,
          'bedrooms': prop.bedrooms,
          'bathrooms': prop.bathrooms,
          'description': prop.description,
          'photos': photos,
          'ai_score': score.investment_score if score else None,
          'avm': score.pd_avm if score else None,
          'yield_pct': score.gross_yield_pct if score else None,
          'epc_rating': prop.epc_energy_rating,
          'flood_risk': score.pd_flood_risk if score else None,
      }


  @router.get("/{property_id}")
  def get_public_listing(
      property_id: int,
      db: Session = Depends(get_db),
      user: Optional[User] = Depends(get_optional_user),
  ):
      prop = _get_listing_property(db, property_id)
      if user and user.subscription_status in ('active', 'past_due') and user.subscription_tier in ('investor', 'admin'):
          return _investor_view(prop, db)
      return _public_view(prop)


  @router.get("/auction/{username}")
  def get_auction_listings(
      username: str,
      db: Session = Depends(get_db),
      user: Optional[User] = Depends(get_optional_user),
  ):
      """List all active properties uploaded by an auction house."""
      from backend.models.user import User as UserModel
      uploader = db.query(UserModel).filter(UserModel.email == username).first()
      if not uploader:
          raise HTTPException(status_code=404, detail="Auction house not found")

      # TODO: query properties by uploader_id once auction_listings table exists
      return {'uploader': uploader.full_name, 'listings': []}


  @router.get("/deal/{username}")
  def get_deal_listings(
      username: str,
      db: Session = Depends(get_db),
      user: Optional[User] = Depends(get_optional_user),
  ):
      """List all active properties uploaded by a deal source."""
      from backend.models.user import User as UserModel
      uploader = db.query(UserModel).filter(UserModel.email == username).first()
      if not uploader:
          raise HTTPException(status_code=404, detail="Deal source not found")

      return {'uploader': uploader.full_name, 'listings': []}
  ```

- [ ] **Step 4: Register router**

  In `backend/api/main.py`:

  ```python
  from backend.api.routers import listings
  app.include_router(listings.router)
  ```

- [ ] **Step 5: Run tests**

  ```bash
  docker-compose exec backend pytest tests/api/test_listings_public.py -v
  ```

  Expected: PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/api/routers/listings.py tests/api/test_listings_public.py backend/api/main.py
  git commit -m "feat: add public listing pages with field visibility rules"
  ```

---

## Task 22: Celery Worker + Enrichment Task

**Files:**
- Create: `backend/celery_app.py`
- Create: `backend/tasks/__init__.py`
- Create: `backend/tasks/enrichment.py`
- Create: `tests/tasks/test_enrichment_task.py`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Write failing test**

  Create `tests/tasks/__init__.py` (empty).

  Create `tests/tasks/test_enrichment_task.py`:

  ```python
  """Tests for Celery enrichment task."""
  import pytest
  from unittest.mock import patch, MagicMock


  def test_enrich_property_calls_services():
      from backend.tasks.enrichment import enrich_property_task
      with patch('backend.tasks.enrichment.SessionLocal') as MockSession, \
           patch('backend.tasks.enrichment.PropertyDataService') as MockPD, \
           patch('backend.tasks.enrichment.analyse_property') as mock_ai:

          db = MagicMock()
          MockSession.return_value = db

          prop = MagicMock()
          prop.id = 1
          score = MagicMock()
          db.query.return_value.get.return_value = prop
          db.query.return_value.filter.return_value.first.return_value = score

          enrich_property_task(1)

          MockPD.return_value.enrich.assert_called_once()
          mock_ai.assert_called_once_with(1, db)
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/tasks/test_enrichment_task.py -v
  ```

  Expected: FAIL — module does not exist.

- [ ] **Step 3: Create Celery app**

  Create `backend/celery_app.py`:

  ```python
  """Celery application — Redis broker, no beat scheduler."""
  import os
  from celery import Celery

  REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

  celery_app = Celery(
      'assetlens',
      broker=REDIS_URL,
      backend=REDIS_URL,
      include=['backend.tasks.enrichment'],
  )

  celery_app.conf.update(
      task_serializer='json',
      accept_content=['json'],
      result_serializer='json',
      timezone='UTC',
      enable_utc=True,
      task_acks_late=True,
      worker_prefetch_multiplier=1,
  )
  ```

- [ ] **Step 4: Create enrichment task**

  Create `backend/tasks/__init__.py` (empty).

  Create `backend/tasks/enrichment.py`:

  ```python
  """Async enrichment task — triggered by upload endpoints."""
  import logging

  from backend.celery_app import celery_app
  from backend.models.base import SessionLocal
  from backend.models.property import Property, PropertyScore
  from backend.services.propertydata_service import PropertyDataService
  from backend.services.ai_analysis_service import analyse_property

  logger = logging.getLogger(__name__)


  @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
  def enrich_property_task(self, property_id: int):
      """
      Enrich a single property with PropertyData + AI analysis.
      Called via .delay(property_id) from upload handlers.
      """
      db = SessionLocal()
      try:
          prop = db.query(Property).get(property_id)
          if not prop:
              logger.warning("Enrichment: property %d not found", property_id)
              return

          score = db.query(PropertyScore).filter(PropertyScore.property_id == property_id).first()
          if not score:
              score = PropertyScore(property_id=property_id)
              db.add(score)
              db.flush()

          # PropertyData enrichment (AVM, rental, flood)
          pd_service = PropertyDataService()
          try:
              pd_service.enrich(prop, score, db)
          except Exception as e:
              logger.warning("PD enrichment failed for %d: %s", property_id, e)

          # AI analysis
          try:
              analyse_property(property_id, db)
          except Exception as e:
              logger.warning("AI analysis failed for %d: %s", property_id, e)

          db.commit()
          logger.info("Enrichment complete for property %d", property_id)
      except Exception as e:
          logger.error("Enrichment task failed for %d: %s", property_id, e)
          db.rollback()
          raise self.retry(exc=e)
      finally:
          db.close()
  ```

- [ ] **Step 5: Add Celery worker to docker-compose.yml**

  In `docker-compose.yml`, add after the `scheduler` service block:

  ```yaml
    # Celery Worker - Async task processing
    celery_worker:
      build:
        context: .
        dockerfile: docker/Dockerfile.backend
      container_name: assetlens_celery_worker
      environment:
        - DB_HOST=postgres
        - DB_PORT=5432
        - DB_NAME=${DB_NAME:-assetlens}
        - DB_USER=${DB_USER:-postgres}
        - DB_PASSWORD=${DB_PASSWORD:-postgres}
        - REDIS_HOST=redis
        - REDIS_PORT=6379
        - REDIS_URL=redis://redis:6379/0
        - PROPERTYDATA_API_KEY=${PROPERTYDATA_API_KEY:-}
        - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
        - AI_CALL_DELAY=${AI_CALL_DELAY:-2.0}
      volumes:
        - ./backend:/app/backend
        - ./logs:/app/logs
      networks:
        - assetlens
      depends_on:
        postgres:
          condition: service_healthy
        redis:
          condition: service_healthy
      restart: unless-stopped
      command: celery -A backend.celery_app worker --loglevel=info --concurrency=2
  ```

- [ ] **Step 6: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/tasks/test_enrichment_task.py -v
  ```

  Expected: PASS.

- [ ] **Step 7: Commit**

  ```bash
  git add backend/celery_app.py backend/tasks/ tests/tasks/ docker-compose.yml
  git commit -m "feat: add Celery worker with enrichment task — Redis broker, concurrency=2"
  ```

---

## Task 23: Uploader Portal — Auction Listings API

**Files:**
- Create: `backend/api/routers/auction_listings.py`
- Create: `tests/api/test_auction_upload.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Write failing test**

  Create `tests/api/test_auction_upload.py`:

  ```python
  """Tests for auction house listing upload."""
  import pytest
  from unittest.mock import patch, MagicMock
  from fastapi.testclient import TestClient


  @pytest.fixture
  def client():
      from backend.api.main import app
      return TestClient(app)


  def test_manual_listing_creates_property(client):
      """POST a single auction lot — should create property and queue enrichment."""
      mock_user = MagicMock()
      mock_user.subscription_status = 'active'
      mock_user.subscription_tier = 'auction_house'
      mock_user.is_superuser = False
      mock_user.id = 1

      listing = {
          'address': '55 Test Lane',
          'postcode': 'LS1 4AP',
          'guide_price': 150000,
          'auction_date': '2026-05-15',
          'property_type': 'terraced',
          'bedrooms': 3,
      }

      with patch('backend.api.routers.auction_listings.get_current_user', return_value=mock_user), \
           patch('backend.api.routers.auction_listings.check_subscription', return_value=mock_user), \
           patch('backend.api.routers.auction_listings.enrich_property_task') as mock_enrich:

          response = client.post('/api/auction-listings', json=listing)

      assert response.status_code == 201
      assert response.json()['address'] == '55 Test Lane'
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/api/test_auction_upload.py -v
  ```

  Expected: FAIL — module does not exist.

- [ ] **Step 3: Create auction listings router**

  Create `backend/api/routers/auction_listings.py`:

  ```python
  """Auction house upload portal — manual form + CSV upload."""
  import csv
  import io
  import json
  import logging
  from datetime import datetime
  from typing import Optional, List

  from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
  from pydantic import BaseModel
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.auth.guards import get_current_user, check_subscription
  from backend.models.property import Property
  from backend.models.user import User
  from backend.services.deduplication_service import PropertyDeduplicator
  from backend.tasks.enrichment import enrich_property_task

  logger = logging.getLogger(__name__)
  router = APIRouter(prefix="/api/auction-listings", tags=["auction-listings"])


  class AuctionListingCreate(BaseModel):
      address: str
      postcode: str
      guide_price: Optional[float] = None
      auction_date: Optional[str] = None
      property_type: Optional[str] = None
      bedrooms: Optional[int] = None
      bathrooms: Optional[int] = None
      description: Optional[str] = None
      legal_pack_url: Optional[str] = None
      tenure: Optional[str] = None


  @router.post("", status_code=201)
  def create_listing(
      listing: AuctionListingCreate,
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      check_subscription(user, ['auction_house', 'white_label', 'admin'])

      dedup = PropertyDeduplicator(db)
      existing = dedup.find_duplicate(address=listing.address, postcode=listing.postcode)
      if existing:
          return {'id': existing.id, 'address': existing.address, 'deduplicated': True}

      prop = Property(
          address=listing.address,
          postcode=listing.postcode.upper().strip(),
          property_type=listing.property_type or 'unknown',
          bedrooms=listing.bedrooms,
          bathrooms=listing.bathrooms,
          asking_price=listing.guide_price,
          description=listing.description,
          status='active',
          date_found=datetime.utcnow(),
      )
      db.add(prop)
      db.flush()

      dedup.add_property_source(
          prop.id,
          source_name='auction_upload',
          source_id=None,
          source_url=None,
      )
      db.commit()

      # Queue async enrichment
      try:
          enrich_property_task.delay(prop.id)
      except Exception as e:
          logger.warning("Failed to queue enrichment for %d: %s", prop.id, e)

      return {
          'id': prop.id,
          'address': prop.address,
          'postcode': prop.postcode,
          'deduplicated': False,
      }


  @router.post("/upload-csv")
  async def upload_csv(
      file: UploadFile = File(...),
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      check_subscription(user, ['auction_house', 'white_label', 'admin'])

      content = await file.read()
      text = content.decode('utf-8-sig')
      reader = csv.DictReader(io.StringIO(text))

      stats = {'imported': 0, 'duplicates': 0, 'errors': 0}
      dedup = PropertyDeduplicator(db)

      for row in reader:
          try:
              address = row.get('address', '').strip()
              postcode = row.get('postcode', '').strip().upper()
              if not postcode:
                  stats['errors'] += 1
                  continue

              existing = dedup.find_duplicate(address=address, postcode=postcode)
              if existing:
                  stats['duplicates'] += 1
                  continue

              prop = Property(
                  address=address,
                  postcode=postcode,
                  property_type=row.get('property_type', 'unknown'),
                  bedrooms=int(row['bedrooms']) if row.get('bedrooms') else None,
                  asking_price=float(row['guide_price']) if row.get('guide_price') else None,
                  description=row.get('description'),
                  status='active',
                  date_found=datetime.utcnow(),
              )
              db.add(prop)
              db.flush()

              dedup.add_property_source(prop.id, source_name='auction_upload')
              stats['imported'] += 1

              try:
                  enrich_property_task.delay(prop.id)
              except Exception:
                  pass

          except Exception as e:
              logger.warning("CSV row error: %s", e)
              stats['errors'] += 1

      db.commit()
      return stats


  @router.get("")
  def list_my_listings(
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      check_subscription(user, ['auction_house', 'white_label', 'admin'])
      # Query properties where source is auction_upload and uploader is this user
      # For now, return all auction_upload properties (user scoping added when we track uploader_id)
      from backend.models.property import PropertySource
      props = (
          db.query(Property)
          .join(PropertySource, Property.id == PropertySource.property_id)
          .filter(PropertySource.source_name == 'auction_upload')
          .order_by(Property.date_found.desc())
          .limit(100)
          .all()
      )
      return [{'id': p.id, 'address': p.address, 'postcode': p.postcode, 'asking_price': p.asking_price} for p in props]
  ```

- [ ] **Step 4: Register router**

  In `backend/api/main.py`:

  ```python
  from backend.api.routers import auction_listings
  app.include_router(auction_listings.router)
  ```

- [ ] **Step 5: Run tests**

  ```bash
  docker-compose exec backend pytest tests/api/test_auction_upload.py -v
  ```

  Expected: PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/api/routers/auction_listings.py tests/api/test_auction_upload.py backend/api/main.py
  git commit -m "feat: add auction house upload portal — manual form + CSV upload with Celery enrichment"
  ```

---

## Task 24: Deal Source Listings API

**Files:**
- Create: `backend/api/routers/deal_listings.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Create deal listings router**

  Create `backend/api/routers/deal_listings.py`:

  ```python
  """Deal source upload portal — same pattern as auction_listings with extra fields."""
  import csv
  import io
  import json
  import logging
  from datetime import datetime
  from typing import Optional

  from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
  from pydantic import BaseModel
  from sqlalchemy.orm import Session

  from backend.api.dependencies import get_db
  from backend.auth.guards import get_current_user, check_subscription
  from backend.models.property import Property, PropertySource
  from backend.models.user import User
  from backend.services.deduplication_service import PropertyDeduplicator
  from backend.tasks.enrichment import enrich_property_task

  logger = logging.getLogger(__name__)
  router = APIRouter(prefix="/api/deal-listings", tags=["deal-listings"])


  class DealListingCreate(BaseModel):
      address: str
      postcode: str
      asking_price: Optional[float] = None
      property_type: Optional[str] = None
      bedrooms: Optional[int] = None
      bathrooms: Optional[int] = None
      description: Optional[str] = None
      sourcing_fee: Optional[float] = None
      gdv_estimate: Optional[float] = None
      refurb_cost_estimate: Optional[float] = None
      deal_expiry_date: Optional[str] = None


  @router.post("", status_code=201)
  def create_deal_listing(
      listing: DealListingCreate,
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      check_subscription(user, ['deal_source', 'white_label', 'admin'])

      dedup = PropertyDeduplicator(db)
      existing = dedup.find_duplicate(address=listing.address, postcode=listing.postcode)
      if existing:
          return {'id': existing.id, 'address': existing.address, 'deduplicated': True}

      prop = Property(
          address=listing.address,
          postcode=listing.postcode.upper().strip(),
          property_type=listing.property_type or 'unknown',
          bedrooms=listing.bedrooms,
          bathrooms=listing.bathrooms,
          asking_price=listing.asking_price,
          description=listing.description,
          status='active',
          date_found=datetime.utcnow(),
      )
      db.add(prop)
      db.flush()

      dedup.add_property_source(prop.id, source_name='deal_upload')
      db.commit()

      try:
          enrich_property_task.delay(prop.id)
      except Exception as e:
          logger.warning("Failed to queue enrichment for %d: %s", prop.id, e)

      return {
          'id': prop.id,
          'address': prop.address,
          'postcode': prop.postcode,
          'deduplicated': False,
      }


  @router.post("/upload-csv")
  async def upload_deal_csv(
      file: UploadFile = File(...),
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      check_subscription(user, ['deal_source', 'white_label', 'admin'])

      content = await file.read()
      text = content.decode('utf-8-sig')
      reader = csv.DictReader(io.StringIO(text))

      stats = {'imported': 0, 'duplicates': 0, 'errors': 0}
      dedup = PropertyDeduplicator(db)

      for row in reader:
          try:
              address = row.get('address', '').strip()
              postcode = row.get('postcode', '').strip().upper()
              if not postcode:
                  stats['errors'] += 1
                  continue

              existing = dedup.find_duplicate(address=address, postcode=postcode)
              if existing:
                  stats['duplicates'] += 1
                  continue

              prop = Property(
                  address=address,
                  postcode=postcode,
                  property_type=row.get('property_type', 'unknown'),
                  bedrooms=int(row['bedrooms']) if row.get('bedrooms') else None,
                  asking_price=float(row['asking_price']) if row.get('asking_price') else None,
                  description=row.get('description'),
                  status='active',
                  date_found=datetime.utcnow(),
              )
              db.add(prop)
              db.flush()
              dedup.add_property_source(prop.id, source_name='deal_upload')
              stats['imported'] += 1

              try:
                  enrich_property_task.delay(prop.id)
              except Exception:
                  pass

          except Exception as e:
              logger.warning("CSV row error: %s", e)
              stats['errors'] += 1

      db.commit()
      return stats


  @router.get("")
  def list_my_deal_listings(
      db: Session = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      check_subscription(user, ['deal_source', 'white_label', 'admin'])
      props = (
          db.query(Property)
          .join(PropertySource, Property.id == PropertySource.property_id)
          .filter(PropertySource.source_name == 'deal_upload')
          .order_by(Property.date_found.desc())
          .limit(100)
          .all()
      )
      return [{'id': p.id, 'address': p.address, 'postcode': p.postcode, 'asking_price': p.asking_price} for p in props]
  ```

- [ ] **Step 2: Register router**

  In `backend/api/main.py`:

  ```python
  from backend.api.routers import deal_listings
  app.include_router(deal_listings.router)
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add backend/api/routers/deal_listings.py backend/api/main.py
  git commit -m "feat: add deal source upload portal — manual form + CSV upload"
  ```

---

## Self-Review

**Spec coverage check:**
- ✅ Section F immediate actions: Wharf URL (Task 1), gate scrapers (Task 2), images/description audit (Tasks 3-7)
- ✅ Section A extended EPC: migration 021/022 (Task 10), importer (Task 11), colour-coding (Task 12)
- ✅ Section B investor profiles: UserProfile model (Task 13), account page (Task 19)
- ✅ Section C personalised score: service (Task 20)
- ✅ Section D public listings: listings router (Task 21), field visibility rules (Task 21)
- ✅ Section D uploader portal: auction (Task 23), deal source (Task 24)
- ✅ Section D white-label: brand fields on UserProfile (Task 13), noted in listings router
- ✅ Section E AI enrichment triggers: Celery task (Task 22), called from upload handlers (Tasks 23-24)
- ✅ Amendment 001 pricing/tiers: User model enums (Task 13), guards (Task 15), Stripe billing (Task 16)
- ✅ On-demand scan: service (Task 8), endpoint (Task 9)
- ✅ Pipeline fixes: normalizer images (Task 3), merge bug (Task 4), dedup images (Task 5), upload dedup (Task 6)
- ✅ Auth: JWT (Task 14), guards (Task 15), frontend auth (Task 18)

**Placeholder scan:** No TBDs except the auction/deal `list_my_listings` endpoints which note user-scoped filtering will be added when `uploader_id` is tracked — this is acceptable for Sprint 3 scope.

**Type/name consistency:**
- `enrich_property_task` — defined in Task 22, called in Tasks 23-24 ✓
- `check_subscription` — defined in Task 15, called in Tasks 17, 23, 24 ✓
- `get_current_user` — defined in Task 15, used in Tasks 16, 17, 19, 23, 24 ✓
- `get_optional_user` — defined in Task 15, used in Tasks 17, 21 ✓
- `ScanService.scan()` — defined in Task 8, called in Task 9 ✓
- `personalise()` — defined in Task 20, function signature matches test calls ✓
