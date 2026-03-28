# Design: Bug Fixes — Cron Scheduler & Sold Property Handling
**Date**: 2026-03-28
**Status**: Approved
**Scope**: Phase 1 Bug Fixes — items 1 and 2

---

## Context

Two bugs identified from live testing:

1. **Cron not running** — ETL jobs are defined and scripted but no cron daemon exists in any container. Sources are never automatically updated.
2. **Sold properties persisting** — The feed importer hardcodes `status='active'` on every property regardless of what Searchland returns. Properties that have been sold at auction or gone STC remain visible as active investment opportunities.

---

## Bug 1: Cron Scheduler

### Problem
`scripts/crontab.txt` is never installed. The backend container runs only `uvicorn`. No scheduled ETL has ever run in production.

### Approach
Add a dedicated `scheduler` service to `docker-compose.yml` that shares the backend image and runs a cron daemon. Standard Docker pattern — one container per concern.

### Changes

**`docker/Dockerfile.backend`**
- Add `cron` to the `apt-get install` line
- Add `COPY scripts /app/scripts` so crontab and ETL shell scripts are baked into the production image (Coolify bakes the image; no script volume mount needed in prod)

**`docker-compose.yml`**
- Add `scheduler` service:
  - Same image/build as `backend`
  - Command: `sh -c "crontab /app/scripts/crontab.txt && cron -f"`
  - Same environment variables as `backend` (needs DB + Redis access)
  - Same `depends_on` healthchecks (postgres + redis must be healthy)
  - Shared `./logs:/app/logs` volume
  - Add `./scripts:/app/scripts` volume mount to both `backend` and `scheduler` services (dev only — prod uses baked-in image copy)
  - No exposed ports

**`scripts/crontab.txt`**
- Change health check target from `http://localhost:8000/health` to `http://backend:8000/health` (Docker Compose service name, resolves on the shared `assetlens` network)

### Deployment on Hetzner
No manual steps required. The updated `docker-compose.yml` deploys automatically via the existing `git push hetzner master` → post-receive hook → Coolify deploy workflow. Coolify starts the new `scheduler` service alongside `backend` on next deploy.

---

## Bug 2: Sold Property Handling

### Problem
`normalize_property_data` in `searchland_client.py` always returns `status: 'active'`. `_process_property` in `licensed_feed_importer.py` always creates new records with `status='active'`. Status changes from the API are silently discarded.

Additionally, the incremental feed only returns properties Searchland has recently updated. A property that went sold before the last sync window may never reappear in the feed — it stays active in our DB indefinitely.

### Status Mapping

| Searchland API value | Internal status |
|---|---|
| `for_sale`, `available`, unknown/unrecognised | `active` |
| `stc`, `sold_stc`, `under_offer`, `sale_agreed` | `stc` |
| `sold`, `completed` | `sold` |

### Approach
**STC/Under Offer** — keep visible, add status badge on property card. Deals fall through; an STC property is useful intelligence and is still nominally on the market.
**Sold** — capture sale data to `SalesHistory`, archive the property immediately. Sold properties are not actionable and should not appear in the active feed.

### Changes

**`backend/services/searchland_client.py`** — `normalize_property_data`
- Map real API status field using the table above instead of hardcoding `'active'`
- Also pass through `sold_price` from the API response (may be null)

**`backend/etl/licensed_feed_importer.py`** — `_process_property`
- Branch on incoming status:
  - `active` → existing behaviour (new or update)
  - `stc` → update `property.status = 'stc'`; update `last_seen_at` on source record; property remains visible
  - `sold` → create `SalesHistory` record (sold_price from API if available, else null; sale_date = today); set `property.status = 'sold'`, `property.date_sold = today`; property removed from active feed

**`backend/api/dependencies.py`** — `PropertyFilters`
- Change default status filter from `'active'` to `'active,stc'`
- Update the query builder to split on comma and use `status IN (...)` clause
- STC properties appear by default; users can filter to active-only if needed

**`backend/etl/stale_listing_checker.py`** — new ETL job
- Queries all properties where `status IN ('active', 'stc')` and source `last_seen_at` is older than 7 days
- Re-fetches each from PropertyData by `source_id`
- Processes any status changes using the same branch logic as `_process_property`
- Catches properties that went sold outside the incremental feed window
- Scheduled weekly (Wednesdays) in `run_etl.sh`

**`scripts/run_etl.sh`**
- Add stale listing checker step (weekly on Wednesdays: `[ "$(date +%u)" = "3" ]`)

**Frontend — property card**
- Add STC/Under Offer badge (conditional chip) when `property.status === 'stc'`
- Minimal change — one conditional className/element on the existing card component

### Database
No migration required. `status` is `String(20)` — `'stc'` fits without schema change. `date_sold` already exists on the `Property` model. `SalesHistory` already has the correct shape for a sold record.

---

## Out of Scope
- Price history tracking (Phase 1 item 3 — motivated seller signals)
- Multiple advertiser slots
- Property scoring algorithm changes
