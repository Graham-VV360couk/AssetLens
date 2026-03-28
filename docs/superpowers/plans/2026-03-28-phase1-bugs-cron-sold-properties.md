# Phase 1 Bug Fixes: Cron Scheduler & Sold Property Handling

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the cron scheduler so ETL jobs run nightly, and teach the feed importer to correctly handle sold/STC properties instead of marking everything active forever.

**Architecture:** Bug 1 adds a `scheduler` Docker Compose service sharing the backend image; it installs the existing crontab and runs `cron -f`. Bug 2 threads real status values from the Searchland API through the importer — sold properties get archived with a SalesHistory entry, STC properties stay visible with a badge, and a new weekly `stale_listing_checker` job catches anything that went sold outside the incremental feed window.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Docker Compose, React 18, Tailwind CSS, pytest

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `docker/Dockerfile.backend` | Modify | Add `cron` to apt-get; bake scripts dir into image |
| `docker-compose.yml` | Modify | Add `scheduler` service; add scripts volume |
| `scripts/crontab.txt` | Modify | Fix health check URL to `backend:8000` |
| `database/migrations/versions/020_sales_history_nullable_price.py` | Create | Make `sale_price` nullable — sold events without confirmed price |
| `backend/services/searchland_client.py` | Modify | Map real API status values in `normalize_property_data` |
| `backend/etl/licensed_feed_importer.py` | Modify | Branch on status: active / stc / sold handling |
| `backend/api/dependencies.py` | Modify | Default status filter `'active,stc'` |
| `backend/api/routers/properties.py` | Modify | `_build_query` status filter → `IN` clause |
| `backend/etl/stale_listing_checker.py` | Create | Weekly job: re-check properties not seen in 7+ days |
| `scripts/run_etl.sh` | Modify | Add stale checker step (Wednesdays) |
| `frontend/src/components/ui/PropertyCard.jsx` | Modify | STC badge on card header |
| `tests/etl/test_sold_property_handling.py` | Create | Unit tests for status mapping + importer branching |
| `tests/etl/test_stale_listing_checker.py` | Create | Unit tests for stale checker |

---

## Task 1: Docker — Cron Scheduler Service

**Files:**
- Modify: `docker/Dockerfile.backend`
- Modify: `docker-compose.yml`
- Modify: `scripts/crontab.txt`

- [ ] **Step 1: Add `cron` and scripts to Dockerfile.backend**

  Replace the `apt-get install` block and add the scripts COPY:

  ```dockerfile
  RUN apt-get update && apt-get install -y \
      gcc \
      postgresql-client \
      libpq-dev \
      curl \
      cron \
      && rm -rf /var/lib/apt/lists/*
  ```

  Add after the existing `COPY database /app/database` line:
  ```dockerfile
  COPY scripts /app/scripts
  RUN chmod +x /app/scripts/*.sh
  ```

- [ ] **Step 2: Fix the health check URL in crontab.txt**

  In `scripts/crontab.txt`, change:
  ```
  */15 * * * * curl -sf http://localhost:8000/health > /dev/null || echo "$(date): API health check FAILED" >> /app/logs/health.log
  ```
  to:
  ```
  */15 * * * * curl -sf http://backend:8000/health > /dev/null || echo "$(date): API health check FAILED" >> /app/logs/health.log
  ```

- [ ] **Step 3: Add `scheduler` service and scripts volume to docker-compose.yml**

  In the `backend` service, add `./scripts:/app/scripts` to the existing volumes list:
  ```yaml
  volumes:
    - ./backend:/app/backend
    - ./database:/app/database
    - ./scripts:/app/scripts
    - ./logs:/app/logs
  ```

  Add the `scheduler` service after `backend` (before the `frontend` service):
  ```yaml
  scheduler:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    container_name: assetlens_scheduler
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=${DB_NAME:-assetlens}
      - DB_USER=${DB_USER:-postgres}
      - DB_PASSWORD=${DB_PASSWORD:-postgres}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - APP_ENV=${APP_ENV:-development}
    volumes:
      - ./backend:/app/backend
      - ./database:/app/database
      - ./scripts:/app/scripts
      - ./logs:/app/logs
    networks:
      - assetlens
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: sh -c "crontab /app/scripts/crontab.txt && cron -f"
  ```

- [ ] **Step 4: Build and verify the scheduler starts**

  ```bash
  docker-compose build scheduler
  docker-compose up -d scheduler
  docker-compose logs scheduler
  ```

  Expected: container starts, no errors. Verify crontab installed:
  ```bash
  docker-compose exec scheduler crontab -l
  ```
  Expected: shows the 3 cron entries from `crontab.txt`.

- [ ] **Step 5: Commit**

  ```bash
  git add docker/Dockerfile.backend docker-compose.yml scripts/crontab.txt
  git commit -m "feat: add scheduler container with cron daemon for ETL jobs"
  ```

---

## Task 2: DB Migration — Nullable Sale Price

**Files:**
- Create: `database/migrations/versions/020_sales_history_nullable_price.py`

The `sale_price` column on `sales_history` is currently `NOT NULL`. When a property goes sold but the feed doesn't include the final price, we need to record the sold event without faking a price.

- [ ] **Step 1: Create the migration file**

  Create `database/migrations/versions/020_sales_history_nullable_price.py`:

  ```python
  """Make sales_history.sale_price nullable for feed-sourced sold events

  Revision ID: 020
  Revises: 019
  Create Date: 2026-03-28
  """
  from alembic import op
  import sqlalchemy as sa

  revision = '020'
  down_revision = '019'
  branch_labels = None
  depends_on = None


  def upgrade():
      op.alter_column(
          'sales_history',
          'sale_price',
          existing_type=sa.Float(),
          nullable=True,
      )


  def downgrade():
      # Set any nulls to 0 before making NOT NULL again
      op.execute("UPDATE sales_history SET sale_price = 0 WHERE sale_price IS NULL")
      op.alter_column(
          'sales_history',
          'sale_price',
          existing_type=sa.Float(),
          nullable=False,
      )
  ```

- [ ] **Step 2: Run the migration**

  ```bash
  docker-compose exec backend alembic upgrade head
  ```

  Expected output ends with: `Running upgrade 019 -> 020, Make sales_history.sale_price nullable`

- [ ] **Step 3: Commit**

  ```bash
  git add database/migrations/versions/020_sales_history_nullable_price.py
  git commit -m "feat: make sales_history.sale_price nullable for feed-sourced sold events"
  ```

---

## Task 3: Status Mapping in SearchlandClient

**Files:**
- Modify: `backend/services/searchland_client.py`
- Create: `tests/etl/__init__.py`
- Create: `tests/etl/test_sold_property_handling.py`

- [ ] **Step 1: Create the test file and write failing tests**

  Create `tests/__init__.py` (empty) and `tests/etl/__init__.py` (empty), then create `tests/etl/test_sold_property_handling.py`:

  ```python
  """Tests for status mapping and sold property handling in the feed importer."""
  import pytest
  from unittest.mock import MagicMock, patch
  from datetime import date

  # ── Status mapping tests ──────────────────────────────────────────────────────

  def make_client():
      from backend.services.searchland_client import SearchlandClient
      client = SearchlandClient.__new__(SearchlandClient)
      return client


  def normalize(raw_status):
      client = make_client()
      raw = {
          'id': '123',
          'url': 'http://example.com',
          'address': {'display_address': '1 Test St', 'postcode': 'SW1A 1AA',
                      'town': 'London', 'county': 'Greater London'},
          'property_type': 'flat',
          'bedrooms': 2,
          'bathrooms': 1,
          'price': 300000,
          'description': '',
          'status': raw_status,
          'sold_price': None,
      }
      return client.normalize_property_data(raw)


  @pytest.mark.parametrize('raw_status', ['for_sale', 'available', None, 'unknown_future_value'])
  def test_active_statuses_map_to_active(raw_status):
      result = normalize(raw_status)
      assert result['status'] == 'active'


  @pytest.mark.parametrize('raw_status', ['stc', 'sold_stc', 'under_offer', 'sale_agreed'])
  def test_stc_statuses_map_to_stc(raw_status):
      result = normalize(raw_status)
      assert result['status'] == 'stc'


  @pytest.mark.parametrize('raw_status', ['sold', 'completed'])
  def test_sold_statuses_map_to_sold(raw_status):
      result = normalize(raw_status)
      assert result['status'] == 'sold'


  def test_sold_price_passed_through():
      client = make_client()
      raw = {
          'id': '123', 'url': 'http://example.com',
          'address': {'display_address': '1 Test St', 'postcode': 'SW1A 1AA',
                      'town': 'London', 'county': 'Greater London'},
          'property_type': 'flat', 'bedrooms': 2, 'bathrooms': 1,
          'price': 300000, 'description': '', 'status': 'sold', 'sold_price': 285000,
      }
      result = client.normalize_property_data(raw)
      assert result['sold_price'] == 285000
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  docker-compose exec backend pytest tests/etl/test_sold_property_handling.py -v -k "status"
  ```

  Expected: FAIL — `normalize_property_data` returns `status: 'active'` for all inputs.

- [ ] **Step 3: Update `normalize_property_data` in searchland_client.py**

  Find the `normalize_property_data` method. Replace the hardcoded `'status': 'active'` and the `'imported_at'` line with:

  ```python
  _STATUS_MAP = {
      'for_sale': 'active',
      'available': 'active',
      'stc': 'stc',
      'sold_stc': 'stc',
      'under_offer': 'stc',
      'sale_agreed': 'stc',
      'sold': 'sold',
      'completed': 'sold',
  }

  def normalize_property_data(self, raw_property: Dict[str, Any]) -> Dict[str, Any]:
      """
      Normalize property data from Searchland API to AssetLens schema
      """
      raw_status = (raw_property.get('status') or '').lower()
      mapped_status = self._STATUS_MAP.get(raw_status, 'active')

      return {
          'source': 'searchland',
          'source_id': raw_property.get('id'),
          'source_url': raw_property.get('url'),
          'address': raw_property.get('address', {}).get('display_address'),
          'postcode': raw_property.get('address', {}).get('postcode'),
          'town': raw_property.get('address', {}).get('town'),
          'county': raw_property.get('address', {}).get('county'),
          'property_type': raw_property.get('property_type'),
          'bedrooms': raw_property.get('bedrooms'),
          'bathrooms': raw_property.get('bathrooms'),
          'asking_price': raw_property.get('price'),
          'sold_price': raw_property.get('sold_price'),
          'description': raw_property.get('description'),
          'date_found': datetime.utcnow().date(),
          'status': mapped_status,
          'imported_at': datetime.utcnow()
      }
  ```

  Note: `_STATUS_MAP` is a class-level attribute, defined just before `normalize_property_data`.

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/etl/test_sold_property_handling.py -v -k "status or sold_price"
  ```

  Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/searchland_client.py tests/
  git commit -m "feat: map real Searchland status values in normalize_property_data"
  ```

---

## Task 4: Feed Importer — Status Branching

**Files:**
- Modify: `backend/etl/licensed_feed_importer.py`
- Modify: `tests/etl/test_sold_property_handling.py` (extend)

- [ ] **Step 1: Add importer branching tests to the test file**

  Append to `tests/etl/test_sold_property_handling.py`:

  ```python
  # ── Importer branching tests ──────────────────────────────────────────────────

  from backend.models.property import Property, PropertySource
  from backend.models.sales_history import SalesHistory


  def _make_property(status='active', asking_price=300000):
      prop = Property(
          id=1, address='1 Test St', postcode='SW1A 1AA',
          property_type='flat', bedrooms=2, status=status,
          asking_price=asking_price, date_found=date.today(),
      )
      return prop


  def _make_importer(db):
      from backend.etl.licensed_feed_importer import LicensedFeedImporter
      importer = LicensedFeedImporter.__new__(LicensedFeedImporter)
      importer.db = db
      importer.stats = {'new': 0, 'updated': 0, 'errors': 0, 'skipped': 0, 'fetched': 0}
      return importer


  def test_stc_status_updates_property_status():
      """An STC property in the feed updates the property status to 'stc' and stays visible."""
      db = MagicMock()
      prop = _make_property(status='active')
      importer = _make_importer(db)
      importer._apply_status_change(prop, 'stc', sold_price=None)
      assert prop.status == 'stc'
      assert prop.date_sold is None


  def test_sold_status_archives_property():
      """A sold property gets archived and date_sold set."""
      db = MagicMock()
      prop = _make_property(status='active', asking_price=300000)
      importer = _make_importer(db)
      importer._apply_status_change(prop, 'sold', sold_price=285000)
      assert prop.status == 'sold'
      assert prop.date_sold == date.today()
      db.add.assert_called_once()
      sales_record = db.add.call_args[0][0]
      assert isinstance(sales_record, SalesHistory)
      assert sales_record.sale_price == 285000


  def test_sold_without_price_uses_none():
      """A sold property with no confirmed price stores sale_price=None."""
      db = MagicMock()
      prop = _make_property(status='active', asking_price=300000)
      importer = _make_importer(db)
      importer._apply_status_change(prop, 'sold', sold_price=None)
      assert prop.status == 'sold'
      db.add.assert_called_once()
      sales_record = db.add.call_args[0][0]
      assert sales_record.sale_price is None


  def test_active_status_no_change():
      """An active property coming through the feed makes no status change."""
      db = MagicMock()
      prop = _make_property(status='active')
      importer = _make_importer(db)
      importer._apply_status_change(prop, 'active', sold_price=None)
      assert prop.status == 'active'
      db.add.assert_not_called()
  ```

- [ ] **Step 2: Run to verify failures**

  ```bash
  docker-compose exec backend pytest tests/etl/test_sold_property_handling.py -v -k "importer or stc or sold_status or sold_without or active_status"
  ```

  Expected: FAIL — `_apply_status_change` does not exist.

- [ ] **Step 3: Add `_apply_status_change` to LicensedFeedImporter**

  In `backend/etl/licensed_feed_importer.py`, add this import at the top (with the other model imports):

  ```python
  from backend.models.sales_history import SalesHistory
  ```

  Add the following method to the `LicensedFeedImporter` class, after `_geocode_property`:

  ```python
  def _apply_status_change(self, prop: Property, new_status: str, sold_price):
      """
      Update property status based on feed signal.
      - 'stc'  → mark STC, property stays visible
      - 'sold' → write SalesHistory, archive property
      - 'active' → no change
      """
      if new_status == 'stc':
          prop.status = 'stc'
      elif new_status == 'sold':
          prop.status = 'sold'
          prop.date_sold = datetime.utcnow().date()
          self.db.add(SalesHistory(
              property_id=prop.id,
              address=prop.address,
              postcode=prop.postcode,
              sale_date=datetime.utcnow().date(),
              sale_price=sold_price,  # None if feed doesn't include confirmed price
              property_type=prop.property_type,
          ))
  ```

- [ ] **Step 4: Wire `_apply_status_change` into `_process_property`**

  In `_process_property`, after the `if duplicate:` block (after `self.stats['updated'] += 1`) and after the `else:` block (after `self.stats['new'] += 1`), call `_apply_status_change` in both branches.

  Replace the existing `_process_property` method with:

  ```python
  def _process_property(self, raw: dict):
      normalized = self.client.normalize_property_data(raw)
      incoming_status = normalized.get('status', 'active')
      sold_price = normalized.get('sold_price')

      duplicate = self.deduplicator.find_duplicate(
          address=normalized.get('address', ''),
          postcode=normalized.get('postcode', ''),
      )

      if duplicate:
          self.deduplicator.merge_property_data(duplicate, normalized)
          self.deduplicator.add_property_source(
              duplicate.id,
              source_name=normalized.get('source', 'searchland'),
              source_id=str(normalized.get('source_id', '')),
              source_url=normalized.get('source_url', ''),
          )
          if duplicate.latitude is None and duplicate.postcode:
              self._geocode_property(duplicate)
          self._apply_status_change(duplicate, incoming_status, sold_price)
          self.stats['updated'] += 1
      else:
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
          )
          self.db.add(prop)
          self.db.flush()
          self.deduplicator.add_property_source(
              prop.id,
              source_name=normalized.get('source', 'searchland'),
              source_id=str(normalized.get('source_id', '')),
              source_url=normalized.get('source_url', ''),
          )
          if prop.postcode:
              self._geocode_property(prop)
          self._apply_status_change(prop, incoming_status, sold_price)
          self.stats['new'] += 1
  ```

- [ ] **Step 5: Run all importer tests**

  ```bash
  docker-compose exec backend pytest tests/etl/test_sold_property_handling.py -v
  ```

  Expected: all tests PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/etl/licensed_feed_importer.py tests/etl/test_sold_property_handling.py
  git commit -m "feat: handle sold/STC status in feed importer with SalesHistory recording"
  ```

---

## Task 5: API Multi-Status Filter

**Files:**
- Modify: `backend/api/dependencies.py`
- Modify: `backend/api/routers/properties.py`

- [ ] **Step 1: Update default status in `dependencies.py`**

  Find line 45 in `backend/api/dependencies.py`:
  ```python
  status: Optional[str] = Query('active'),
  ```
  Change to:
  ```python
  status: Optional[str] = Query('active,stc'),
  ```

- [ ] **Step 2: Update `_build_query` in `properties.py` to use `IN` clause**

  Find lines 40–41 in `backend/api/routers/properties.py`:
  ```python
  if filters.status:
      q = q.filter(Property.status == filters.status)
  ```
  Replace with:
  ```python
  if filters.status:
      statuses = [s.strip() for s in filters.status.split(',') if s.strip()]
      if len(statuses) == 1:
          q = q.filter(Property.status == statuses[0])
      else:
          q = q.filter(Property.status.in_(statuses))
  ```

- [ ] **Step 3: Verify the API responds correctly**

  ```bash
  # Default — should return active + STC
  curl -s "http://localhost:8000/api/properties?page_size=5" | python -m json.tool | grep '"status"'

  # Explicit active-only
  curl -s "http://localhost:8000/api/properties?status=active&page_size=5" | python -m json.tool | grep '"status"'

  # STC-only
  curl -s "http://localhost:8000/api/properties?status=stc&page_size=5" | python -m json.tool | grep '"status"'
  ```

  Expected: default returns both active and stc properties; `status=active` returns only active; `status=stc` returns only stc.

- [ ] **Step 4: Commit**

  ```bash
  git add backend/api/dependencies.py backend/api/routers/properties.py
  git commit -m "feat: multi-status filter for properties API — default shows active+stc"
  ```

---

## Task 6: Stale Listing Checker ETL Job

**Files:**
- Create: `backend/etl/stale_listing_checker.py`
- Modify: `scripts/run_etl.sh`
- Create: `tests/etl/test_stale_listing_checker.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/etl/test_stale_listing_checker.py`:

  ```python
  """Tests for stale listing checker ETL job."""
  import pytest
  from unittest.mock import MagicMock, patch, call
  from datetime import datetime, timedelta, date


  def _make_stale_property(days_old=10):
      prop = MagicMock()
      prop.id = 1
      prop.address = '1 Test St'
      prop.postcode = 'SW1A 1AA'
      prop.property_type = 'flat'
      prop.status = 'active'
      prop.asking_price = 300000
      prop.date_sold = None
      source = MagicMock()
      source.source_name = 'searchland'
      source.source_id = 'SL123'
      source.last_seen_at = datetime.utcnow() - timedelta(days=days_old)
      prop.sources = [source]
      return prop


  def test_fresh_properties_are_skipped():
      """Properties last seen within 7 days are not re-fetched."""
      from backend.etl.stale_listing_checker import StaleListingChecker
      db = MagicMock()
      db.query.return_value.filter.return_value.all.return_value = []
      checker = StaleListingChecker(db)
      stats = checker.run()
      assert stats['rechecked'] == 0


  def test_stale_active_property_is_rechecked():
      """A property not seen for 8 days is included in the recheck batch."""
      from backend.etl.stale_listing_checker import StaleListingChecker
      stale_prop = _make_stale_property(days_old=8)
      db = MagicMock()
      db.query.return_value.join.return_value.filter.return_value.all.return_value = [stale_prop]

      with patch.object(StaleListingChecker, '_recheck_property', return_value='active') as mock_recheck:
          checker = StaleListingChecker(db)
          stats = checker.run()

      mock_recheck.assert_called_once_with(stale_prop)
      assert stats['rechecked'] == 1


  def test_sold_outcome_archives_property():
      """When re-check returns 'sold', property is archived."""
      from backend.etl.stale_listing_checker import StaleListingChecker
      from backend.models.sales_history import SalesHistory
      stale_prop = _make_stale_property(days_old=10)
      db = MagicMock()

      checker = StaleListingChecker(db)
      checker._apply_sold(stale_prop, sold_price=None)

      assert stale_prop.status == 'sold'
      assert stale_prop.date_sold == date.today()
      db.add.assert_called_once()
      record = db.add.call_args[0][0]
      assert isinstance(record, SalesHistory)


  def test_stc_outcome_updates_status():
      """When re-check returns 'stc', property status is set to stc."""
      from backend.etl.stale_listing_checker import StaleListingChecker
      stale_prop = _make_stale_property(days_old=10)
      db = MagicMock()
      checker = StaleListingChecker(db)
      checker._apply_stc(stale_prop)
      assert stale_prop.status == 'stc'
  ```

- [ ] **Step 2: Run to verify failures**

  ```bash
  docker-compose exec backend pytest tests/etl/test_stale_listing_checker.py -v
  ```

  Expected: FAIL — module `backend.etl.stale_listing_checker` does not exist.

- [ ] **Step 3: Create `backend/etl/stale_listing_checker.py`**

  ```python
  """
  Stale Listing Checker ETL Job
  Re-checks active/STC properties that haven't been seen in the feed for 7+ days.
  Catches properties that went sold outside the incremental feed window.
  Runs weekly on Wednesdays via run_etl.sh.
  """
  import logging
  import os
  import sys
  from datetime import datetime, timedelta, date

  from sqlalchemy.orm import Session

  sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

  from backend.models.base import SessionLocal
  from backend.models.property import Property, PropertySource
  from backend.models.sales_history import SalesHistory
  from backend.services.searchland_client import SearchlandClient

  logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
  logger = logging.getLogger(__name__)

  STALE_AFTER_DAYS = 7


  class StaleListingChecker:
      def __init__(self, db: Session):
          self.db = db
          self.client = SearchlandClient()
          self.stats = {'rechecked': 0, 'sold': 0, 'stc': 0, 'still_active': 0, 'errors': 0}

      def run(self):
          cutoff = datetime.utcnow() - timedelta(days=STALE_AFTER_DAYS)
          stale = (
              self.db.query(Property)
              .join(PropertySource, Property.id == PropertySource.property_id)
              .filter(
                  Property.status.in_(['active', 'stc']),
                  PropertySource.is_active == True,
                  PropertySource.last_seen_at < cutoff,
              )
              .all()
          )
          logger.info("Found %d stale properties to recheck", len(stale))

          for prop in stale:
              try:
                  outcome = self._recheck_property(prop)
                  self.stats['rechecked'] += 1
                  if outcome == 'sold':
                      self.stats['sold'] += 1
                  elif outcome == 'stc':
                      self.stats['stc'] += 1
                  else:
                      self.stats['still_active'] += 1
              except Exception as e:
                  logger.warning("Recheck failed for property %d: %s", prop.id, e)
                  self.stats['errors'] += 1

          self.db.commit()
          logger.info("Stale check complete: %s", self.stats)
          return self.stats

      def _recheck_property(self, prop: Property) -> str:
          """Fetch current status from PropertyData by source_id. Returns 'active', 'stc', or 'sold'."""
          source = next(
              (s for s in prop.sources if s.source_name in ('searchland', 'propertydata') and s.source_id),
              None,
          )
          if not source:
              return 'active'

          try:
              fresh = self.client.get_property_by_id(source.source_id)
          except Exception:
              return 'active'  # Can't reach API — assume still active, retry next week

          if not fresh:
              # Not found in API — possibly delisted; treat as sold without price
              self._apply_sold(prop, sold_price=None)
              return 'sold'

          raw_status = (fresh.get('status') or '').lower()
          mapped = self.client._STATUS_MAP.get(raw_status, 'active')

          if mapped == 'sold':
              self._apply_sold(prop, sold_price=fresh.get('sold_price'))
              return 'sold'
          elif mapped == 'stc':
              self._apply_stc(prop)
              return 'stc'
          else:
              # Still active — update last_seen_at
              source.last_seen_at = datetime.utcnow()
              return 'active'

      def _apply_sold(self, prop: Property, sold_price):
          prop.status = 'sold'
          prop.date_sold = date.today()
          self.db.add(SalesHistory(
              property_id=prop.id,
              address=prop.address,
              postcode=prop.postcode,
              sale_date=date.today(),
              sale_price=sold_price,
              property_type=prop.property_type,
          ))

      def _apply_stc(self, prop: Property):
          prop.status = 'stc'


  def main():
      db = SessionLocal()
      try:
          checker = StaleListingChecker(db)
          checker.run()
      finally:
          db.close()


  if __name__ == '__main__':
      main()
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  docker-compose exec backend pytest tests/etl/test_stale_listing_checker.py -v
  ```

  Expected: all 4 tests PASS.

- [ ] **Step 5: Add stale checker to `run_etl.sh`**

  In `scripts/run_etl.sh`, add after the Step 4 rental block and before Step 5 (scoring):

  ```bash
  # Step 4b: Stale listing checker (weekly on Wednesdays)
  if [ "$(date +%u)" = "3" ]; then
      run_job "Stale Listing Checker" "$RUN_CMD -m backend.etl.stale_listing_checker" || true
  fi
  ```

  Note: use `-m backend.etl.stale_listing_checker` (module invocation) since the file uses `sys.path.insert` and has a `main()` guard.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/etl/stale_listing_checker.py scripts/run_etl.sh tests/etl/test_stale_listing_checker.py
  git commit -m "feat: stale listing checker — weekly re-check for properties gone sold outside feed window"
  ```

---

## Task 7: STC Badge on Property Card

**Files:**
- Modify: `frontend/src/components/ui/PropertyCard.jsx`

- [ ] **Step 1: Add the STC badge to the card header**

  In `PropertyCard.jsx`, find the existing badges block (lines ~51–60). The block currently renders `PriceBandBadge`, AI verdict badge, and Reviewed badge. Add the STC badge after `PriceBandBadge`:

  ```jsx
  {score && <PriceBandBadge band={score.price_band} size="sm" />}
  {property.status === 'stc' && (
    <span className="inline-flex items-center text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-amber-500/20 text-amber-300 border-amber-500/40">
      STC
    </span>
  )}
  {verdict && (
  ```

- [ ] **Step 2: Verify in browser**

  Start the frontend dev server and load the Properties page. If you have any STC properties in the database, verify the amber "STC" badge appears on their cards. If not, temporarily set one property to `status='stc'` via psql:

  ```sql
  UPDATE properties SET status = 'stc' WHERE id = (SELECT id FROM properties LIMIT 1);
  ```

  Reload the Properties page and confirm the badge appears. Revert:
  ```sql
  UPDATE properties SET status = 'active' WHERE id = (SELECT id FROM properties LIMIT 1);
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/components/ui/PropertyCard.jsx
  git commit -m "feat: STC badge on property card for sold-subject-to-contract listings"
  ```

---

## Task 8: Check SearchlandClient Has `get_property_by_id`

**Files:**
- Modify: `backend/services/searchland_client.py` (if method is missing)

The stale listing checker calls `self.client.get_property_by_id(source_id)`. This method may not exist yet.

- [ ] **Step 1: Check if `get_property_by_id` exists**

  ```bash
  grep -n "get_property_by_id" backend/services/searchland_client.py
  ```

  If output is non-empty, skip to Task 9. If empty, continue.

- [ ] **Step 2: Add `get_property_by_id` to SearchlandClient**

  Add the following method to `SearchlandClient`, after `get_properties`:

  ```python
  def get_property_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
      """
      Fetch a single property by its Searchland/PropertyData ID.
      Returns the raw property dict, or None if not found.
      """
      try:
          result = self._make_request(f'properties/{source_id}')
          return result.get('property') or result
      except Exception as e:
          if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
              return None
          raise
  ```

- [ ] **Step 3: Run the full test suite**

  ```bash
  docker-compose exec backend pytest tests/ -v
  ```

  Expected: all tests PASS.

- [ ] **Step 4: Commit (if changed)**

  ```bash
  git add backend/services/searchland_client.py
  git commit -m "feat: add get_property_by_id to SearchlandClient for stale recheck"
  ```

---

## Self-Review

**Spec coverage check:**
- ✅ Bug 1: Cron daemon in Docker → Task 1
- ✅ Bug 1: Scripts baked into image for production → Task 1
- ✅ Bug 1: Health check URL fixed → Task 1
- ✅ Bug 2: Status mapping from Searchland → Task 3
- ✅ Bug 2: STC kept visible, sold archived → Task 4
- ✅ Bug 2: SalesHistory written on sold → Task 4
- ✅ Bug 2: API default filter includes STC → Task 5
- ✅ Bug 2: Stale listing checker for feed gaps → Task 6
- ✅ Bug 2: STC badge on frontend → Task 7
- ✅ Migration for nullable sale_price → Task 2
- ✅ `get_property_by_id` needed by stale checker → Task 8

**Type/name consistency:**
- `_apply_status_change` defined in Task 4, called in Task 4 only ✅
- `_apply_sold` / `_apply_stc` defined in stale checker Task 6, tested in Task 6 ✅
- `_STATUS_MAP` defined as class attribute in Task 3, accessed via `self.client._STATUS_MAP` in Task 6 ✅
- `SalesHistory.source` field used in Tasks 4 and 6 — check this column exists on the model before running

**Confirmed:** `SalesHistory` has no `source` column — the constructors in Tasks 4 and 6 do not pass one. ✅
