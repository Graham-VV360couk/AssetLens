# AssetLens — Data Points Addendum Implementation Design

**Date:** 2026-04-02
**Status:** Approved
**Source documents:**
- `.claude/ASSETLENS_DATA_POINTS_ADDENDUM.md`
- `.claude/ASSETLENS_DATA_POINTS_ADDENDUM_001.md` (Amendment 001 — Pricing & Tiers)
- `.claude/ASSETLENS_PHASE1_ROADMAP.md`

**Scope:** Three sprints covering data layer fixes, auth/billing, and revenue features. Transforms AssetLens from a listing intelligence platform into an on-demand property research tool for any UK address.

---

## Sprint Structure

| Sprint | Name | Core Deliverable | Depends on |
|--------|------|-----------------|------------|
| **1** | Data Layer | Immediate fixes, pipeline repair, on-demand property scan, extended EPC fields (if capacity) | Nothing |
| **2** | Auth & Billing | User model, FastAPI-Users + JWT, Stripe subscriptions, investor profiles, free trial gating | Sprint 1 |
| **3** | Revenue Features | Personalised AI deal score, public listing pages, uploader portal, Celery worker | Sprint 2 |

---

## Cross-Cutting Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth stack | FastAPI-Users + JWT (self-hosted) | Subscription model needs same-transaction access to user/profile/trial data. Avoids Supabase sync problem. passlib/bcrypt/cryptography already in requirements.txt. |
| Task queue | Celery + Redis (worker only, no beat) | Upload-triggered enrichment needs durable queue that survives restarts. Redis already running for cache. Beat scheduler deferred until scheduled re-enrichment needed. |
| Billing | Stripe Checkout + Customer Portal | Standard for SaaS. Annual discount in Stripe Price objects, not app code. Webhook-driven status updates. |
| Core product model | On-demand property research for any UK address | Differentiator vs EIS (who own auction workflow). Scraped listings and auction lots are discovery channels feeding the research tool. |

---

## Pricing & Tier Reference

Source: Amendment 001 (`.claude/ASSETLENS_DATA_POINTS_ADDENDUM_001.md`)

| Tier | Monthly | Annual | Who |
|------|---------|--------|-----|
| Public visitor | Free | — | No account |
| Free trial | Free | — | Account created, view-count gated |
| Investor | £99/mo | £990/yr | Buyers, BTL investors, developers |
| Auction House | £55/mo | £550/yr | Auction houses listing lots |
| Deal Source | £55/mo | £550/yr | Property sourcers listing deals |
| White Label | £199/mo | £1,990/yr | Uploaders wanting branded pages |
| Admin | Internal | — | GeekyBee staff |

**Free trial:** 3 property views + 3 AI score views. No time limit. Full access (not degraded). Hard paywall on either limit.

**Dual-role:** A user can hold both Investor and an uploader role. Two Stripe Subscriptions on the same Customer ID. Combined permissions.

**Annual billing:** 10 months' price (2 months free). Discount in Stripe Price objects.

---

## Sprint 1: Data Layer

### 1.1 Immediate Actions (Section F)

**Wharf Financial URL:**
- File: `frontend/src/pages/PropertyDetail.jsx`
- Change: Find "Get Funding Quote" button, replace URL with `https://propertyfundingplatform.com/WharfFinancial#!/allloans`
- Ensure: `target="_blank" rel="noopener noreferrer"`

**Gate Data Sources page:**
- File: `frontend/src/App.jsx` (or router config)
- Change: Wrap `/scrapers` route behind env-var admin check (`REACT_APP_ADMIN_EMAILS` or similar)
- Temporary measure until real auth in Sprint 2

**Audit findings (from codebase exploration):**
- **Property description:** Field exists in DB model (`Property.description`), licensed feed importer writes it for new properties, but `PropertyDetail.jsx` does not render it anywhere. **Display bug confirmed.**
- **Property images:** `image_url` (single) renders as hero image. `image_urls` (JSON array) exists in model but is **not populated by the main Searchland pipeline** and has no gallery component. **Pipeline + display bug confirmed.**

### 1.2 Pipeline Fixes

**Priority:** These must land before Sprint 3. The uploader portal needs a working merge/dedup pipeline before auction house CSV imports can land cleanly.

#### Bug 1 — Searchland normaliser missing image extraction

- File: `backend/services/searchland_client.py` → `normalize_property_data()`
- Problem: Method does not extract image data from API response
- Fix: Add `image_url` and `image_urls` extraction from raw API response (confirm Searchland field names — likely `images` array or `photos`)
- If API does not expose images: document as "not available from this source", images only come via scraper layer

#### Bug 2 — Licensed feed merge call wrong signature

- File: `backend/etl/licensed_feed_importer.py` ~line 105
- Problem: `self.deduplicator.merge_property_data(duplicate, normalized)` missing required params
- Fix: Pass `source_name`, `source_id`, `source_url` from normalized data

#### Bug 3 — Deduplication service ignores image fields

- File: `backend/services/deduplication_service.py` → `merge_property_data()`
- Problem: Does not merge `image_url` or `image_urls` fields
- Fix: Add conditional merge — fill if target property's field is empty, don't overwrite existing

#### Enhancement — Dedup coverage for uploaded properties

- File: `backend/services/deduplication_service.py`
- The dedup service matches on fuzzy address + postcode. Must verify it handles:
  - Full address match: uploaded lot matches scraped property exactly → merge
  - Postcode-only upload (auction house provides postcode, no street address) → must NOT false-match, create new record
  - Near-miss addresses (typos, abbreviations) → existing fuzzy matching should catch
- Add test cases for all three scenarios. This is Sprint 1 work — Sprint 3's uploader portal depends on it.

#### Frontend — description + image gallery

- File: `frontend/src/pages/PropertyDetail.jsx`
- Add: Description block below hero section (render `property.description` if present)
- Add: Image gallery component. If `image_urls` JSON array exists, render thumbnails with lightbox. Fall back to single `image_url`. Fall back to no-image placeholder.

### 1.3 On-Demand Property Scan

The core product feature. Any UK address (or postcode for auction edge cases) returns a full intelligence profile.

**New endpoint:** `POST /api/scan`

Input:
```json
{
  "address": "string (optional)",
  "postcode": "string (required)"
}
```

Process:
1. Dedup check — if property already exists in DB, return cached data (re-enrich if stale >7 days)
2. If not cached, orchestrate parallel lookups:
   - Land Registry sales history (postcode + address fuzzy match)
   - EPC certificate (postcode + address)
   - PropertyData API: AVM, rental estimate, flood risk, planning constraints
   - Area stats (postcode district — existing endpoint logic)
3. Create Property record with `source='on_demand_scan'`
4. Run scoring service
5. Trigger AI analysis (async — may not complete before response)
6. Return full property profile (AI insight arrives later via polling)

**Postcode-only fallback (auction edge case):**
- Skip property-specific lookups (no LR match, no EPC match)
- Return area-level data: average prices, yield estimates, growth trends, flood risk zone, EPC band distribution
- Response includes `scan_type: 'area'` vs `scan_type: 'property'`

**Caching:** Scanned properties persist with `source='on_demand_scan'`. Cache-hit scans burn zero API credits. Stale threshold: 7 days.

**API credit management:** ~3 PropertyData credits per fresh scan. Sprint 2 adds per-user rate limiting via subscription tier.

**Sprint 2 dependency note:** This endpoint launches unauthenticated in Sprint 1 for development/testing. Sprint 2 wraps it in `require_active_subscription(['investor', 'admin'])` + trial view counter.

### 1.4 Extended EPC Fields (if Sprint 1 has capacity)

**Slippable to Sprint 2 without consequence.** No other sprint depends on extended EPC fields.

#### Migration 021 — add Tier 1 columns to `epc_certificates`

| Column | Type | Source CSV field |
|--------|------|-----------------|
| `construction_age_band` | String 50 | `CONSTRUCTION_AGE_BAND` |
| `current_energy_efficiency` | Integer | `CURRENT_ENERGY_EFFICIENCY` |
| `potential_energy_efficiency` | Integer | `POTENTIAL_ENERGY_EFFICIENCY` |
| `tenure` | String 50 | `TENURE` |
| `mains_gas_flag` | String 1 | `MAINS_GAS_FLAG` |
| `heating_cost_current` | Float | `HEATING_COST_CURRENT` |
| `heating_cost_potential` | Float | `HEATING_COST_POTENTIAL` |
| `hot_water_cost_current` | Float | `HOT_WATER_COST_CURRENT` |
| `hot_water_cost_potential` | Float | `HOT_WATER_COST_POTENTIAL` |
| `lighting_cost_current` | Float | `LIGHTING_COST_CURRENT` |
| `lighting_cost_potential` | Float | `LIGHTING_COST_POTENTIAL` |
| `co2_emissions_current` | Float | `CO2_EMISSIONS_CURRENT` |
| `number_habitable_rooms` | Integer | `NUMBER_HABITABLE_ROOMS` |
| `transaction_type` | String 50 | `TRANSACTION_TYPE` |
| `epc_expiry_date` | Date | Computed: `inspection_date + 10 years` |

#### Migration 022 — add extended fields to `epc_recommendations`

| Column | Type | Source CSV field |
|--------|------|-----------------|
| `typical_saving` | Float | `TYPICAL_SAVING` |
| `efficiency_rating_before` | Integer | `ENERGY_EFFICIENCY_RATING_A` |
| `efficiency_rating_after` | Integer | `ENERGY_EFFICIENCY_RATING_B` |

#### EPC importer extension

- File: `backend/etl/epc_importer.py`
- Extend CSV column mapping to populate new Tier 1 fields
- Compute `epc_expiry_date = inspection_date + 10 years` during import

#### Frontend — EPC colour-coding (Section A4)

Update EPCPanel component with colour rules:

| Data point | Green | Amber | Red |
|-----------|-------|-------|-----|
| EPC band | A, B, C | D, E | F, G |
| Component efficiency | Very Good, Good | Average | Poor, Very Poor |
| Construction age | Post-1990 | 1950–1990 | Pre-1950 |
| EPC expiry | >2 years remaining | <2 years | Expired |
| Mains gas | Y | — | N |
| CO2 emissions | <3 tonnes/yr | 3–6 | >6 |
| Efficiency gap (current vs potential) | <10 points | >20 | >35 |

---

## Sprint 2: Auth & Billing

### 2.1 User Model

#### Migration 023 — `users` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `email` | String 255, unique, indexed | Login identifier |
| `hashed_password` | String 255 | bcrypt via passlib |
| `full_name` | String 200 | |
| `company_name` | String 200, nullable | For uploaders |
| `phone` | String 20, nullable | |
| `role` | Enum: `investor`, `auction_house`, `deal_source`, `admin` | Selected at signup |
| `subscription_status` | Enum: `trial`, `active`, `past_due`, `cancelled` | Set by Stripe webhook |
| `subscription_tier` | Enum: `none`, `investor`, `auction_house`, `deal_source`, `white_label`, `admin` | Set by Stripe webhook |
| `stripe_customer_id` | String 100, nullable, unique | |
| `stripe_subscription_id` | String 100, nullable | Primary subscription |
| `stripe_subscription_id_secondary` | String 100, nullable | Dual-role (investor + uploader) |
| `trial_property_views` | Integer, default 0 | Free trial counter |
| `trial_ai_views` | Integer, default 0 | Free trial counter |
| `is_active` | Boolean, default True | FastAPI-Users managed |
| `is_superuser` | Boolean, default False | Admin flag |
| `is_verified` | Boolean, default False | Email verification |
| `created_at`, `updated_at` | DateTime | |

#### Migration 024 — `user_profiles` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `user_id` | Integer FK → users, unique | |
| **Financial capacity** | | |
| `max_deposit` | Integer, nullable | £ |
| `loan_type_sought` | String 50, nullable | bridging / commercial / development / btl |
| `max_loan_wanted` | Integer, nullable | £, NULL = max available |
| `loan_term_months` | Integer, nullable | |
| `purpose` | String 20, nullable | purchase / refinance |
| **Portfolio & experience** | | |
| `investment_experience` | String 20, nullable | first_time / 1_5_yrs / 5_plus / professional |
| `properties_owned` | Integer, nullable | |
| `portfolio_value_band` | String 20, nullable | under_250k / 250k_500k / 500k_1m / over_1m |
| `outstanding_mortgage_band` | String 20, nullable | Same bands |
| `hmo_experience` | Boolean, nullable | |
| `development_experience` | Boolean, nullable | |
| `limited_company` | Boolean, nullable | |
| `company_name_ch` | String 200, nullable | Companies House registered name |
| `companies_house_number` | String 20, nullable | |
| `spv` | Boolean, nullable | Special Purpose Vehicle |
| `personal_guarantee_willing` | Boolean, nullable | |
| **Personal circumstances** | | |
| `main_residence` | Boolean, nullable | Affects SDLT (3% surcharge if no) |
| `uk_resident` | Boolean, nullable | Non-UK = 2% SDLT surcharge |
| `employment_status` | String 20, nullable | employed / self_employed / director / retired |
| `annual_income_band` | String 20, nullable | under_30k / 30_60k / 60_100k / over_100k |
| `credit_history` | String 20, nullable | clean / minor_blips / adverse |
| **Investment preferences** | | |
| `target_location` | String 200, nullable | Region or specific postcode |
| `strategy` | String 30, nullable | btl / hmo / flip / development / brrr |
| `readiness` | String 20, nullable | immediate / near_future / researching |
| **GDPR** | | |
| `broker_consent_given_at` | DateTime, nullable | Required before funding quote pre-fill |
| `profile_deletion_at` | DateTime, nullable | When user requested financial data deletion |
| **Uploader settings** | | |
| `auction_form_field_prefs` | Text (JSON), nullable | Array of field names toggled off |
| `brand_logo_url` | String 500, nullable | White-label tier |
| `brand_primary_colour` | String 7, nullable | White-label hex colour |
| `brand_accent_colour` | String 7, nullable | White-label hex colour |
| `custom_subdomain` | String 200, nullable | White-label CNAME |
| `created_at`, `updated_at` | DateTime | |

### 2.2 FastAPI-Users + JWT

**Package:** `fastapi-users[sqlalchemy]` (add to requirements.txt)

**Configuration:**
- JWT secret: `JWT_SECRET` env var
- Access token: 30 minute lifetime
- Refresh token: 7 day lifetime
- Transport: Cookie for browser, Bearer header for API clients

**Endpoints (provided by FastAPI-Users):**
- `POST /api/auth/register` — creates user with `subscription_status=trial`, counters at 0
- `POST /api/auth/login` — returns JWT pair
- `POST /api/auth/logout` — invalidates refresh token
- `POST /api/auth/refresh` — rotates access token
- `POST /api/auth/forgot-password` — email reset link
- `POST /api/auth/reset-password` — completes reset
- `POST /api/auth/verify` — email verification

**Custom registration schema:** Extends FastAPI-Users default with `role` field:
- "I want to evaluate properties" → `role=investor`
- "I represent an auction house" → `role=auction_house`
- "I source properties for investors" → `role=deal_source`

### 2.3 Route Guards & Access Control

**Backend dependency pattern:**

```python
def require_active_subscription(tiers: list[str]):
    """Reusable dependency — checks subscription status and tier."""
    def checker(user=Depends(current_active_user)):
        if user.is_superuser:
            return user  # Admin bypasses all checks
        if user.subscription_status == 'trial':
            # Check view counters, raise 402 if limit hit
            ...
        if user.subscription_status not in ('active', 'trial', 'past_due'):
            raise HTTPException(403, "Subscription required")
        if user.subscription_tier not in tiers:
            # Check secondary subscription for dual-role users
            ...
        return user
    return checker
```

**Route assignments:**

| Endpoint | Guard |
|----------|-------|
| `POST /api/scan` | `require_active_subscription(['investor', 'admin'])` + trial counter |
| `GET /api/properties/{id}` (full detail) | `require_active_subscription(['investor', 'admin'])` + trial counter |
| `GET /api/ai/insights/{id}` | `require_active_subscription(['investor', 'admin'])` + trial AI counter |
| `POST /api/auction-listings/*` | `require_active_subscription(['auction_house', 'white_label', 'admin'])` |
| `POST /api/deal-listings/*` | `require_active_subscription(['deal_source', 'white_label', 'admin'])` |
| `GET/POST /api/scrapers/*` | `require_active_subscription(['admin'])` |
| Public listing routes | No auth |
| `GET /api/properties` (list view) | No auth (limited fields for unauthenticated) |
| `GET /api/dashboard/*` | `require_active_subscription(['investor', 'admin'])` |

**Trial gating:**
- Each full property view: increment `trial_property_views`, check ≤ 3
- Each AI score view: increment `trial_ai_views`, check ≤ 3
- On limit hit: return HTTP 402 `{ paywall: true, reason: 'trial_limit_reached' }`
- Frontend catches 402, shows paywall modal

**`past_due` grace:** 7 days matching Stripe retry window. Access continues during grace period. Banner shown in UI.

### 2.4 Stripe Integration

**Stripe Price objects (created in Stripe Dashboard):**

| Product | Monthly Price | Annual Price |
|---------|-------------|-------------|
| Investor | £99 | £990 |
| Auction House | £55 | £550 |
| Deal Source | £55 | £550 |
| White Label | £199 | £1,990 |

Annual = 10 months upfront. Discount logic in Stripe, not app code.

**New endpoints:**

`POST /api/billing/create-checkout-session`
- Input: `{ price_id, billing_period: 'monthly' | 'annual' }`
- Creates Stripe Checkout Session, creates Customer if first time
- Returns `{ checkout_url }` — frontend redirects

`POST /api/billing/webhook`
- Stripe webhook receiver with signature verification
- Events:
  - `customer.subscription.created` → `subscription_status=active`, set tier from metadata
  - `customer.subscription.updated` → update tier (plan changes, white-label upgrade)
  - `customer.subscription.deleted` → `subscription_status=cancelled`, revoke immediately
  - `invoice.payment_failed` → `subscription_status=past_due`, 7-day grace

`POST /api/billing/portal-session`
- Creates Stripe Customer Portal session for self-serve management
- Returns `{ portal_url }` — linked from account settings

**Dual-role:** Two Subscription objects on same Customer. Webhook handler checks all active subscriptions, sets `subscription_tier` to highest applicable. `stripe_subscription_id_secondary` stores the second.

### 2.5 Frontend Auth Pages

**New pages:**

| Route | Page | Content |
|-------|------|---------|
| `/login` | Login | Email + password, register link, forgot password link |
| `/register` | Register | Email, password, full name, role selector (3 options), company name (if uploader) |
| `/forgot-password` | Forgot Password | Email input, sends reset link |
| `/reset-password` | Reset Password | New password form (from email link) |
| `/account` | Account Settings | Profile form, investor profile (Section B fields), Stripe portal link, delete financial profile button |

**Components:**
- Auth context provider wrapping app
- `<ProtectedRoute>` component — checks JWT validity + tier
- Paywall modal — plan comparison cards, monthly/annual toggle, Stripe checkout redirect
- `past_due` warning banner below nav

**Layout changes:**
- Sidebar: user name + tier badge when authenticated, login/register links when not
- Role badge colours: investor=blue, auction_house=amber, deal_source=green, white_label=purple, admin=red

### 2.6 Investor Profile (Section B)

**Profile form on `/account` page.** All fields voluntary. Grouped into:
1. Financial capacity (deposit, loan type, max loan, term, purpose)
2. Portfolio & experience (experience level, properties owned, portfolio value, HMO/dev experience, Ltd Co, SPV, personal guarantee)
3. Personal circumstances (main residence, UK resident, employment, income, credit history)
4. Investment preferences (target location, strategy, readiness)

**GDPR compliance:**
- Two consent checkboxes required before Wharf Financial pre-fill activates
- Store `broker_consent_given_at` timestamp on consent
- "Delete my financial profile" button NULLs all financial columns, sets `profile_deletion_at`, retains account

**Wharf Financial integration:**
- Phase 1 (this sprint): Button opens URL in new tab, investor fills in manually
- Phase 2 (future): Wire profile data to pre-fill via API once propertyfundingplatform.com confirms integration method
- Consent gate: Button always visible. Pre-fill only activates after both GDPR checkboxes ticked.

---

## Sprint 3: Revenue Features

### 3.1 Personalised AI Deal Score (Section C)

**Architecture:**
- Base score: existing `property_scores.investment_score` (0-100), calculated at scrape/scan, stored
- Personalised score: base + profile adjustment delta, calculated at request time, NOT stored
- AI commentary: regenerated per investor type using cached base data — no extra PropertyData API calls

**New service:** `backend/services/personalised_score_service.py`

```
personalise(property_score, user_profile) → PersonalisedScore
```

**Adjustment logic (from addendum Section C2):**

| Profile signal | Adjustment |
|---------------|------------|
| Strategy = BTL, no HMO experience | Upweight rental yield. Add HMO compliance note if HMO-viable. |
| Strategy = Flip/development | Upweight AVM gap + planning. Downweight yield. Surface GDV + build cost. |
| Experience = First-time | Plain-English commentary. Flag complexity prominently. |
| Credit history = Adverse | Flag limited mortgage options. Surface bridging as primary route. |
| UK resident = No | Auto-add 2% SDLT surcharge. |
| Main residence = No | Apply 3% additional dwelling surcharge. |
| Max deposit < 25% of asking | Flag deposit shortfall for bridging/commercial. |
| Readiness = Researching | Educational tone. Area trends over urgency. |
| Target location ≠ property location | Yellow banner. No score reduction. |

**Strategy-specific score labels:**

| Strategy | UI Label |
|----------|----------|
| btl | BTL Score X/10 |
| hmo | HMO Score X/10 |
| flip | Flip Score X/10 |
| development | Development Score X/10 |
| brrr | BRRR Score X/10 |
| (none set) | Deal Score X/10 |

**API change:** `GET /api/properties/{id}` response gains `personalised_score` object when user is authenticated investor with a profile. Unauthenticated/trial users see base score only.

**Frontend changes:**
- ScoreGauge: show strategy-specific label
- Personalised commentary block below AI insight panel
- Location mismatch yellow banner at top of PropertyDetail

### 3.2 Public Listing Pages (Section D)

**New routes (no auth required):**

| Route | Content |
|-------|---------|
| `GET /listing/{id}` | Single property, public view |
| `GET /listings/auction/{username}` | All active listings for auction house |
| `GET /listings/deal/{username}` | All active listings for deal source |

**Field visibility (Section D1):**

| Field | Public (no login) | Investor (logged in) |
|-------|-------------------|---------------------|
| Address | Town/area only | Full |
| Postcode | District only (e.g. LS6) | Full |
| Asking/guide price | Visible | Visible |
| Property type/beds/baths | Visible | Visible |
| Photos | Max 3 | All + floor plan |
| Description | Visible | Visible |
| EPC band | Visible if disclosed | Full EPC modal |
| Legal pack URL (auction) | Visible | Visible |
| Solicitor contact | Hidden | Visible |
| Sourcing fee (deal) | Hidden | Visible |
| GDV/refurb cost (deal) | Hidden | Visible |
| Deal expiry | Visible | Visible |
| AI deal score | Hidden | Visible |
| AVM/valuation | Hidden | Visible |
| Yield calculation | Hidden | Visible |
| Comparables | Hidden | Visible |
| Planning history | Hidden | Visible |
| Flood risk | Hidden | Visible |
| Enquire button | Visible (opens login prompt) | Visible (direct enquiry) |

**Backend:** New router `backend/api/routers/listings.py`. Separate serialiser strips gated fields based on auth status.

**Uploader-controlled field hiding (Section D2):**
- `user_profiles.auction_form_field_prefs` JSON stores disabled field names
- Disabled fields stored as NULL, shown as "Not disclosed" in all views
- Settings UI in uploader portal — toggle switches per field
- Default: all fields ON

### 3.3 White-Label Tier (Section D3)

| Feature | Standard (£55/mo) | White Label (£199/mo) |
|---------|-------------------|----------------------|
| Public page URL | `assetlens.geekybee.net/listings/{username}` | `listings.{uploaderdomain}.com` (CNAME) |
| Branding | Uploader name + AssetLens logo | Uploader logo + colours only |
| Theme | Default dark | Custom primary/accent from profile |
| "Powered by AssetLens" | Shown | Hidden |

**Implementation:** Public listing page reads uploader profile. If `subscription_tier === 'white_label'`, applies `brand_primary_colour` / `brand_accent_colour` and hides AssetLens branding. CNAME routing at reverse proxy level (nginx/Coolify custom domain config).

### 3.4 Uploader Portal

**Auction House endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auction-listings/upload-csv` | CSV bulk upload |
| POST | `/api/auction-listings` | Manual form entry |
| GET | `/api/auction-listings` | List own listings |
| PUT | `/api/auction-listings/{id}` | Edit listing |
| DELETE | `/api/auction-listings/{id}` | Remove listing |
| PUT | `/api/auction-listings/field-prefs` | Configure form field visibility |

**Deal Source endpoints:** Same CRUD pattern at `/api/deal-listings/*`. Additional fields: sourcing fee, GDV estimate, refurb cost estimate.

**CSV upload flow:**
1. Upload CSV → validate columns → parse rows
2. Per row: run dedup check (Sprint 1's enhanced dedup handles uploaded-vs-scraped)
3. Create Property records with `source='auction_upload'` or `source='deal_upload'`
4. Queue each `property_id` to Celery for AI enrichment
5. Return `{ imported: N, duplicates: N, errors: N }`

### 3.5 Celery Worker (Section E)

**Scope:** Worker only. No beat scheduler. No Flower monitoring yet.

**New files:**
- `backend/celery_app.py` — init with Redis broker (`REDIS_URL`)
- `backend/tasks/enrichment.py` — `enrich_property(property_id)` task, extracted from existing inline logic

**Docker service:**
```yaml
celery_worker:
  build: { context: ., dockerfile: docker/Dockerfile.backend }
  command: celery -A backend.celery_app worker --loglevel=info --concurrency=2
  environment: [same as backend]
  depends_on: [postgres, redis]
```

**Trigger points:**
- Auction CSV upload completion → `.delay(property_id)` per row
- Auction manual form save → `.delay(property_id)`
- Deal source CSV upload → `.delay(property_id)` per row
- Deal source manual form save → `.delay(property_id)`

**Rate limiting:** Task internally respects `AI_CALL_DELAY` and PropertyData credit pacing. Concurrency=2.

### 3.6 AI Enrichment Trigger Points (Section E)

| Entry route | Trigger |
|-------------|---------|
| Scraped property (Rightmove) | Existing pipeline at point of scrape |
| On-demand scan | Sprint 1 — inline during scan request |
| Auction CSV upload | Queue per property_id after CSV import |
| Auction manual form | Queue property_id after DB write |
| Deal source CSV upload | Queue per property_id after CSV import |
| Deal source manual form | Queue property_id after DB write |
| Re-enrichment | Not in scope. Future: trigger on >5% price change or planning status change. |

**Caching rule:** Base AI enrichment stored on property record, served from cache. Personalised score adjustment (Section C2) calculated at request time using cached base data — no additional PropertyData API calls per investor view.

---

## Pre-Go-Live Infrastructure

From Phase 1 roadmap (still applies):
- **Hetzner:** Add 128 GB volume to primary Coolify server before go-live with real users

---

## Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Data Points Addendum | `.claude/ASSETLENS_DATA_POINTS_ADDENDUM.md` | Extended EPC, investor profiles, personalised score, public listings, AI triggers |
| Amendment 001 — Pricing & Tiers | `.claude/ASSETLENS_DATA_POINTS_ADDENDUM_001.md` | Full subscription structure, access matrix, Stripe gating |
| Phase 1 Roadmap | `.claude/ASSETLENS_PHASE1_ROADMAP.md` | Completed Phase 1 work, Phase 2 backlog |
| Progress | `PROGRESS.md` | Phases 1-7 completion record |
| This document | `docs/superpowers/specs/2026-04-02-addendum-implementation-design.md` | Implementation design for addendum sprints |
