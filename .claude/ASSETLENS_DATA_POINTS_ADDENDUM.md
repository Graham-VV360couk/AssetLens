# Asset Lens — Data Points Supplementary Addendum

**Append to:** AssetLens Full Roadmap & Immediate Priorities  
**For:** Claude VSCode  
**Status:** Confirmed spec — implement as written

This addendum supplements the original Data Points Reference document. It covers four areas not captured in the original: extended EPC fields, investor profile data, the personalised AI deal score, and public listing field visibility rules. All sections use the same data sources (Rightmove, PropertyData API, Land Registry, AI layer) and HIGH / MEDIUM / LOW impact weighting as the original document.

---

## F. Immediate Actions — Do Before Any Sprint

These are single-file or single-line changes. Make them now, before Sprint 1 begins. No dependencies on auth, migrations, or any sprint deliverable.

| Action | File | Change |
|---|---|---|
| Update Wharf Financial URL | `frontend/src/pages/PropertyDetail.jsx` | Find the Get Funding Quote button. Replace current URL with `https://propertyfundingplatform.com/WharfFinancial#!/allloans`. Open in new tab: `target="_blank" rel="noopener noreferrer"` |
| Gate Data Sources page (admin only) | `frontend/src/App.jsx` or router config | Wrap `/scrapers` route in a simple admin check — env-var token or hardcoded admin email list until full auth is in place. Stops non-admin users seeing the page. |
| Confirm property images display | `frontend/src/pages/PropertyDetail.jsx` | Audit whether scraped images are being displayed. If scraper captures image URLs and they are in the DB, confirm they render on PropertyDetail. Log finding. |
| Confirm property description display | `frontend/src/pages/PropertyDetail.jsx` | Same audit for description field. Confirm whether scraped description text renders. Log finding. |

---

## A. Extended EPC Data Fields (Stream 1 — Sprint 1)

The original document captured only the 11 EPC fields currently imported. Stream 1 defines 25+ additional fields split across Tier 1 (import in Sprint 1) and Tier 2 (import next sprint). All come from the MHCLG bulk EPC dataset already in the pipeline — this is a migration and importer extension, not a new data source.

**Pipeline note:** All EPC fields are stored in `epc_certificates` and `epc_recommendations` tables. The AI enrichment pipeline already runs at point of scrape — update it to consume these new fields once migration `020` is applied.

### A1. Tier 1 — Import in Sprint 1 (migration 020)

| Field (CSV column) | Source | DB column | How it affects value / score |
|---|---|---|---|
| `CONSTRUCTION_AGE_BAND` | EPC / MHCLG | `construction_age_band` | Infers build quality, EPC upgrade cost, renovation likelihood. Pre-1950 = higher refurb cost flag. |
| `CURRENT_ENERGY_EFFICIENCY` | EPC / MHCLG | `current_energy_efficiency` | Numeric 0–100 score. Used in AI deal score — low score = mandatory upgrade cost before 2028 BTL compliance. |
| `POTENTIAL_ENERGY_EFFICIENCY` | EPC / MHCLG | `potential_energy_efficiency` | Score after recommended improvements. Gap between current and potential = estimated improvement headroom. |
| `TENURE` | EPC / MHCLG | `tenure` | Owner-occupied / rental private / social. Confirms current use — important for BTL investors checking rental history. |
| `MAINS_GAS_FLAG` | EPC / MHCLG | `mains_gas_flag` | Y/N. No mains gas = higher heating costs, oil or electric dependency — running cost red flag for tenants. |
| `HEATING_COST_CURRENT` | EPC / MHCLG | `heating_cost_current` | Annual £. Direct running cost — factors into net yield and tenant affordability. |
| `HEATING_COST_POTENTIAL` | EPC / MHCLG | `heating_cost_potential` | Annual £ after improvements. Shows saving achievable — supports refurb cost justification. |
| `HOT_WATER_COST_CURRENT` | EPC / MHCLG | `hot_water_cost_current` | Annual £. Part of total running cost profile shown to buyers. |
| `HOT_WATER_COST_POTENTIAL` | EPC / MHCLG | `hot_water_cost_potential` | Annual £ after improvements. |
| `LIGHTING_COST_CURRENT` | EPC / MHCLG | `lighting_cost_current` | Annual £. Minor but part of complete cost picture. |
| `LIGHTING_COST_POTENTIAL` | EPC / MHCLG | `lighting_cost_potential` | Annual £ after improvements. |
| `CO2_EMISSIONS_CURRENT` | EPC / MHCLG | `co2_emissions_current` | Tonnes/yr. Increasingly relevant — lenders beginning to price climate risk. High emissions = future liability. |
| `NUMBER_HABITABLE_ROOMS` | EPC / MHCLG | `number_habitable_rooms` | Critical for HMO scoring. Confirms room count independent of listing data. Used in HMO viability calculation. |
| `TRANSACTION_TYPE` | EPC / MHCLG | `transaction_type` | marketed sale / rental / new dwelling etc. Confirms context of EPC — rental EPC means property has been let before. |
| EPC expiry date | Computed | `epc_expiry_date` | `inspection_date + 10 years`. Flags if certificate is expired or expiring within 2 years — affects legality of re-letting. |

### A2. Tier 2 — Import next sprint

| Field (CSV column) | Source | DB column | How it affects value / score |
|---|---|---|---|
| `WALLS_DESCRIPTION` | EPC / MHCLG | `walls_description` | e.g. "Cavity wall, filled". Indicates insulation status — cavity unfilled = cheap win for EPC upgrade. |
| `WALLS_ENERGY_EFF` | EPC / MHCLG | `walls_energy_eff` | Very Good / Good / Average / Poor / Very Poor. Component-level efficiency rating. |
| `ROOF_DESCRIPTION` | EPC / MHCLG | `roof_description` | Roof construction type and insulation status. |
| `ROOF_ENERGY_EFF` | EPC / MHCLG | `roof_energy_eff` | Component rating. Poor roof = significant heat loss and upgrade cost. |
| `WINDOWS_DESCRIPTION` | EPC / MHCLG | `windows_description` | Single / double / triple glazed. Single glazing = EPC drag and tenant comfort issue. |
| `WINDOWS_ENERGY_EFF` | EPC / MHCLG | `windows_energy_eff` | Component rating. |
| `FLOOR_DESCRIPTION` | EPC / MHCLG | `floor_description` | Suspended / solid. Uninsulated suspended floor = heat loss. |
| `MAINHEAT_DESCRIPTION` | EPC / MHCLG | `mainheat_description` | Boiler type and fuel. Old gas boiler = likely near end of life — replacement cost risk. |
| `MAINHEAT_ENERGY_EFF` | EPC / MHCLG | `mainheat_energy_eff` | Component rating. Poor = significant upgrade required. |
| `LIGHTING_DESCRIPTION` | EPC / MHCLG | `lighting_description` | % low energy lighting. Easy upgrade — quick EPC point gain. |
| `LIGHTING_ENERGY_EFF` | EPC / MHCLG | `lighting_energy_eff` | Component rating. |

### A3. EPC Recommendations extended fields

| Field (CSV column) | Source | DB column | How it affects value / score |
|---|---|---|---|
| `TYPICAL_SAVING` | EPC recommendations | `typical_saving` | Annual £ saving per improvement. Allows AI to calculate total saving potential across all recommendations. |
| `ENERGY_EFFICIENCY_RATING_A` | EPC recommendations | `efficiency_rating_before` | EPC score before this improvement is applied. |
| `ENERGY_EFFICIENCY_RATING_B` | EPC recommendations | `efficiency_rating_after` | EPC score after this improvement. Difference shows each recommendation's contribution to band upgrade. |

### A4. EPC colour-coding rules (EPCDetailModal)

| Data point | Green | Amber / Red |
|---|---|---|
| EPC band | A, B, C | D–E = amber / F–G = red |
| Component efficiency rating | Very Good, Good | Average = amber / Poor, Very Poor = red |
| Construction age band | Post-1990 | 1950–1990 = amber / Pre-1950 = red |
| EPC expiry date | More than 2 years remaining | Under 2 years = amber / Expired = red |
| Mains gas flag | Y (mains gas connected) | N = amber (higher running costs) |
| CO2 emissions | < 3 tonnes/yr | 3–6 = amber / > 6 = red |
| Current vs potential efficiency gap | Gap < 10 points (near ceiling) | Gap > 20 = amber / Gap > 35 = red (major upgrade needed) |

---

## B. Investor Profile Data Fields (Stream 3 — Sprint 2)

Stored on `user_profiles` (FK to `users`). All fields are voluntary.

**Two purposes:**
1. Pre-filling the Wharf Financial funding quote request (Phase 2 — future)
2. Personalising the AI deal score so recommendations match the investor's actual situation

**GDPR requirement:** All financial profile fields are voluntary and clearly marked in the UI. Two consent checkboxes required before funding quote pre-fill activates. Store `broker_consent_given_at` (DateTime, nullable) and `profile_deletion_at` (DateTime, nullable) on `user_profiles`. A "Delete my financial profile" button NULLs all financial columns but retains the account.

### B1. Financial capacity fields

| Field | Options / format | Use in AI personalisation |
|---|---|---|
| Max deposit available | £ free text | Filters out properties requiring larger deposits. Flags LTV mismatch. |
| Loan type sought | Bridging / Commercial / Development / Buy-to-let mortgage | Ensures deal score reflects appropriate finance type. |
| Max loan wanted | Max available (yes) / Specify amount (£) | Used to calculate maximum viable purchase price. |
| Loan term preference | Months / years free text | Short term = bridging / flip preference. Long term = BTL / hold strategy. |
| Purpose | Purchase / Refinance (default: Purchase) | Refinance = portfolio investor, not first purchase. |

### B2. Portfolio & experience fields

| Field | Options / format | Use in AI personalisation |
|---|---|---|
| Investment experience | First-time / 1–5 yrs / 5+ yrs / Professional (10+) | First-time investors get more explanatory AI commentary. Professionals get concise data-led output. |
| Number of properties owned | Integer free text | Context for portfolio growth vs first purchase. |
| Approximate portfolio value | < £250k / £250k–500k / £500k–1m / £1m+ | Higher portfolio value = likely looking for larger or commercial deals. |
| Total outstanding mortgage exposure | Band (same as portfolio value) | High exposure relative to portfolio = serviceability risk flagged by AI. |
| HMO experience | Yes / No | No HMO experience + HMO deal = AI adds compliance and licensing advisory note. |
| Development / refurb experience | Yes / No | No dev experience + heavy refurb deal = AI flags risk and suggests professional advice. |
| Limited company structure | Yes / No → if Yes: company name + Companies House number | Ltd Co purchase affects stamp duty, mortgage products, tax treatment — AI notes implications. |
| SPV (Special Purpose Vehicle) | Yes / No | SPV setup affects finance options — some lenders only lend to SPVs. |
| Personal guarantee willing | Yes / No | Required by most bridging lenders — flags if investor is unwilling. |

### B3. Personal circumstances fields

| Field | Options / format | Use in AI personalisation |
|---|---|---|
| Main residence | Yes / No | Affects stamp duty calculation (3% surcharge if not main residence). |
| UK resident | Yes / No | Non-UK residents face additional SDLT surcharge — AI flags this. |
| Employment status | Employed / Self-employed / Director / Retired | Affects mortgage affordability assessment — self-employed needs 2yr accounts. |
| Annual income | < £30k / £30–60k / £60–100k / £100k+ | Used in mortgage affordability proxy — flags if income unlikely to support proposed borrowing. |
| Credit history | Clean / Minor blips / Adverse (CCJ / defaults) | Adverse credit = limited lender options — AI flags bridging as likely only route. |

### B4. Investment preferences fields

| Field | Options / format | Use in AI personalisation |
|---|---|---|
| Target location | Region dropdown OR specific postcode | Filters deal score — out-of-area deals flagged for this investor. Used in saved search defaults. |
| Readiness to proceed | Immediate / Near future / Just researching | Immediate = show live auction dates and deal expiry urgency. Researching = show more educational context. |

### B5. Wharf Financial funding quote flow

> **Immediate change required:** Update `PropertyDetail.jsx` NOW — change the Get Funding Quote button URL to `https://propertyfundingplatform.com/WharfFinancial#!/allloans`, open in new tab. Single string change — do not wait for Sprint 2.

| Phase | State |
|---|---|
| Phase 1 (now) | Button opens Wharf Financial URL in new tab. Investor fills in manually. Profile data stored locally only — nothing transmitted. |
| Phase 2 (future) | Once propertyfundingplatform.com confirms API / integration method, wire investor profile data programmatically to pre-fill the form. |
| Consent gate | Get Funding Quote button is ALWAYS visible and active. Profile data pre-fill only activates after both GDPR consent checkboxes are ticked. Without consent, button still works — investor fills in manually. |
| Data transmitted (Phase 2) | Loan type, deposit, max loan, term, purpose, experience, Ltd Co status, SPV, personal guarantee, income band, credit history, UK resident, employment status. |

---

## C. Personalised AI Deal Score

The original document defined a generic deal score 1–10 based on property data alone. Now that investor profiles exist, the score must be contextualised to the specific investor viewing the property.

**Architecture:**
- Base score = calculated once at point of scrape, stored on property record (existing pipeline)
- Personalised score = base score + profile adjustment delta, calculated at request time, NOT stored
- AI commentary is regenerated per investor type using cached base data as input — no extra PropertyData API calls

### C1. Base score inputs (already in pipeline)

| Signal | Source | Weight |
|---|---|---|
| Asking price vs AVM | PropertyData `/valuation-sale` | HIGH |
| Claimed yield vs area yield | PropertyData `/yields` | HIGH |
| EPC band (current) | MHCLG EPC dataset | HIGH |
| Flood risk zone | PropertyData `/flood-risk` | HIGH |
| Planning constraints count | PropertyData (multiple) | MEDIUM |
| Lease length (if leasehold) | Land Registry / PropertyData `/title` | HIGH |
| Price growth trend (area) | PropertyData `/growth` | MEDIUM |
| Rental demand score | PropertyData `/demand-rent` | HIGH |
| Days on market (current listing) | Rightmove | MEDIUM |
| EPC upgrade cost estimate | Computed from EPC component ratings + construction age | HIGH |

### C2. Profile-based score adjustments

| Investor profile signal | Adjustment logic | Example output |
|---|---|---|
| Strategy = BTL, no HMO experience | Upweight rental yield signal. Add HMO compliance note if property flagged as HMO viable. | "Strong BTL yield but note HMO licence required if 3+ unrelated tenants — you have not indicated HMO experience." |
| Strategy = Flip / development | Upweight AVM gap and planning history. Downweight rental yield. Surface GDV and build cost prominently. | "Below-market entry price with permitted development potential. Refurb estimate £18k. GDV at current comps: £135k." |
| Experience = First-time investor | Add explanatory plain-English commentary. Flag any complexity (short lease, HMO, listed building) more prominently. | Commentary includes: "As a first-time investor, note that leasehold properties with under 85 years remaining require a lease extension before most lenders will offer a mortgage." |
| Credit history = Adverse | Flag standard BTL mortgage products may not be available. Surface bridging as primary finance route. | "With adverse credit history, standard mortgage products may be limited — bridging finance is likely the most accessible route." |
| UK resident = No | Auto-add SDLT surcharge to stamp duty calculation (2% non-resident surcharge). | Stamp duty estimate includes non-resident surcharge with explanatory note. |
| Main residence = No | Apply 3% SDLT surcharge in stamp duty calculator automatically. | Stamp duty figure updated — 3% additional dwelling surcharge applied. |
| Max deposit < 25% of asking price | Flag if deal requires higher deposit (bridging/commercial lenders require 30–40%). | "Your indicated deposit may be below the minimum required for bridging finance on this property type." |
| Readiness = Just researching | Add educational context. Less urgency framing. Show area trend data more prominently. | Commentary tone shifts from "act now" to "here is what this area has done over 5 years..." |
| Target location ≠ property location | Note location mismatch. Do not reduce score — flag visibly. | Yellow banner: "This property is outside your target area. You are viewing a property in the North West." |

### C3. Strategy-specific score labels

When strategy is set on the investor profile, the score label shown in the UI should reflect it:

| Strategy | Score label shown in UI |
|---|---|
| BTL (Buy to Let) | `BTL Score  X / 10` |
| HMO | `HMO Score  X / 10` |
| Flip / Refurb | `Flip Score  X / 10` |
| Development / Conversion | `Development Score  X / 10` |
| BRRR | `BRRR Score  X / 10` |
| No strategy set | `Deal Score  X / 10` (generic) |

---

## D. Public Listing Field Visibility Rules (Stream 5)

Auction houses and deal sources can embed listings on their own websites via iframe or share a direct public URL. Public pages require no login.

**Route structure:**
- `/listing/{id}` — single property, no login required
- `/listings/auction/{username}` — all active listings for that auction house uploader, no login
- `/listings/deal/{username}` — all active listings for that deal source uploader, no login
- Existing protected routes — investor dashboard with enriched data, AI score, full EPC detail

### D1. Field visibility by access level

| Field | Public (no login) | Investor (logged in) |
|---|---|---|
| Address (full) | Partial — town/area only | Full address |
| Postcode | Partial — district only (e.g. LS6) | Full postcode |
| Asking / guide price | Visible | Visible |
| Property type / beds / baths | Visible | Visible |
| Photos | Max 3 shown | All photos |
| Floor plan | Hidden | Visible |
| Description / notes | Visible | Visible |
| EPC rating (band only) | Visible if disclosed | Full EPC detail modal |
| Legal pack URL (auction) | Visible | Visible |
| Solicitor contact (auction) | Hidden | Visible |
| Sourcing fee (deal source) | Hidden | Visible |
| GDV / refurb cost (deal source) | Hidden | Visible |
| Deal expiry date | Visible | Visible |
| AI deal score | Hidden | Visible |
| AVM / valuation estimate | Hidden | Visible |
| Yield calculation | Hidden | Visible |
| Comparable sold prices | Hidden | Visible |
| Planning history | Hidden | Visible |
| Flood risk / constraints | Hidden | Visible |
| Enquire / contact button | Visible (opens login prompt if not logged in) | Visible (direct enquiry) |

### D2. Uploader-controlled field hiding

Auction houses and deal sources can toggle individual fields off for their upload form. Fields toggled off are stored as NULL and hidden from all views (public and investor). This is separate from the public/investor split above — a field toggled off by the uploader is hidden everywhere.

| Implementation detail | Spec |
|---|---|
| Storage | `auction_form_field_prefs` JSON column on `user_profiles`. Stores array of field names the uploader has disabled. |
| Upload form behaviour | Disabled fields are skipped in tab order, not shown on the form, stored as NULL in DB. |
| Configure form mode | Toggle UI in uploader portal settings — shows all fields with on/off switches. Changes saved to `auction_form_field_prefs`. |
| Investor view | Fields with NULL value and toggled off by uploader show as "Not disclosed" label, not as empty/missing. |
| Public view | Same as investor view — "Not disclosed" label where uploader has hidden a field. |
| Default state | All fields ON by default. Uploader opts out of fields they never use. |

### D3. White-label tier (£199/mo) additional visibility

| Feature | Standard tier (£55/mo) | White-label tier (£199/mo) |
|---|---|---|
| Branding on public page | Uploader name + AssetLens logo | Uploader logo + colours only. AssetLens branding removed. |
| Custom subdomain | `assetlens.geekybee.net/listings/{username}` | `listings.{uploaderdomain}.com` (CNAME setup) |
| Colour theme on iframe | AssetLens default dark theme | Custom primary/accent colour from uploader brand settings |
| "Powered by AssetLens" footer | Shown | Hidden |

---

## E. AI Enrichment Pipeline — Trigger Points

All properties are AI enriched at point of scrape. This section defines the trigger points for the two new entry routes added in Sprint 3.

**Caching rule:** Base AI enrichment results are stored on the property record and served from cache to all investors. The personalised score adjustment (Section C2) is calculated at request time using cached base data — no additional PropertyData API calls are made per investor view.

| Entry route | Trigger behaviour |
|---|---|
| Scraped property (Rightmove) | Existing pipeline — AI enrichment runs at point of scrape. Already implemented. |
| Auction house CSV upload | On successful CSV import, push each new `property_id` to the Celery/Redis job queue. Same enrichment pipeline as scraped properties. |
| Auction house manual form entry | On form save (`POST /api/auction-listings`), push `property_id` to Celery/Redis queue immediately after DB write. |
| Deal source CSV upload | Same as auction house CSV — queue each `property_id` after successful import. |
| Deal source manual form entry | Same as auction house manual — queue `property_id` immediately after DB write. |
| Re-enrichment (future) | Not in scope for Sprint 3. Future: trigger re-enrichment if asking price changes by > 5% or planning status changes. |

---

*End of addendum. Read alongside the original Data Points Reference document and the AssetLens Full Roadmap. All three documents together constitute the full data and build specification.*
