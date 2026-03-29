# AssetLens — Phase 1 Roadmap
**Status**: COMPLETE
**Last Updated**: 2026-03-29
**Scope**: Self-funded work only — no dependency on external investment

---

## Context

Phases 1–7 of the core AssetLens build are complete (see PROGRESS.md). The platform has a working full-stack implementation covering data ingestion, scoring, API, React dashboard, alerts, and deployment.

Phase 1 (this document) covers:
- Bug fixes and UI errors observed in the live product
- Feature additions that strengthen the product for investor conversations
- Quick-win intelligence signals (motivated seller layer)
- Revenue infrastructure (advertising bar)
- The Property Attribute Estimation layer (build spec already written)

Nothing in Phase 1 requires external development funding. Everything here makes the product more compelling *before* that funding conversation happens.

Phase 2 onwards is gated on development funding and is not scoped here.

---

## Phase 1 Items

### 1. Bug Fixes & UI Errors
*(To be populated from live testing notes)*

- [ ] TBC — add observed errors here as they are identified
- [ ] TBC
- [ ] TBC

> **Action**: G to list known bugs/errors seen in the live app. These get prioritised first within Phase 1 as they affect the credibility of the demo product.

---

### 2. Property Attribute Estimation Engine *(moved to Phase 2)*
**Source**: `ASSETLENS_PROPERTY_ATTRIBUTE_ESTIMATION_BUILD_SPEC.md`
**Priority**: High — significant differentiator, spec already written

This is the most substantial Phase 1 build item. Full spec exists. Summary of scope:

#### What it does
Given a property record, estimates and displays likely residential characteristics when exact data is unavailable — with full confidence scoring and source traceability.

#### Attributes covered
- Property type (detached / semi / terrace / flat / bungalow etc.)
- Bedrooms (exact or estimated)
- Bathrooms (exact or range)
- Reception / social spaces
- Internal floor area (sq ft + sqm)
- Plot / land size
- Supporting characteristics (extension, loft, garden size band, outbuildings)

#### Core architectural rule
Every attribute must be labelled: **Known / Inferred / Estimated / Unknown**  
Every non-unknown field carries: confidence score, source type, explanation, last updated.

No naked values. No "AI guessed this, trust us bro" outputs.

#### Confidence bands
| Score | Label |
|-------|-------|
| 0.90–1.00 | Very High |
| 0.75–0.89 | High |
| 0.55–0.74 | Moderate |
| 0.35–0.54 | Low |
| < 0.35 | Very Low |

#### Source priority (example — property type)
1. Land Registry / authoritative transaction data
2. EPC / authoritative housing data
3. Listing extraction
4. Footprint / geometry model
5. Statistical model

#### Key components to build
- `PropertyAttributeEstimator` — main orchestrator
- `PropertyFactCollector` — gathers available facts
- `PropertyInferenceEngine` — applies rules / models
- `PropertyConfidenceScorer` — calculates confidence per field
- `PropertyExplanationBuilder` — generates user-facing reasoning strings

#### UI presentation
New **Property Profile** section on property detail page, grouped as:
- Verified Facts
- Strong Inferences
- Estimated Attributes
- Missing / Unknown

Each field shows: confidence badge, status badge, source badge, hover explanation.

#### User override capability
Users can manually correct key fields. Overrides:
- Store original computed value for audit
- Trigger immediate re-evaluation of dependent attributes
- Update confidence scores and explanations
- Show "Recalculated using your update" indicator

#### Override dependency chain (example)
```
Bedrooms → Bathroom estimate → Reception room estimate → HMO suitability (future)
```

#### Data contradiction detection
If user enters a value that conflicts with underlying data (e.g. 5 bedrooms on a 65 sqm flat), the system should flag the contradiction visibly.

#### MVP approach
Rule-based inference first, ML later. Configurable heuristic ruleset. Examples:
- Terraced 70–95 sqm → likely 2–3 beds
- Semi-detached 85–120 sqm → likely 3 beds
- Detached 140–220 sqm → likely 4–5 beds

#### Build order (from spec)
1. Define output schema
2. Build source resolver
3. Property type estimator
4. Floor area resolver
5. Bedroom estimator
6. Bathroom estimator
7. Reception/social estimator
8. Plot size estimator
9. Confidence scoring
10. Explanation builder
11. API exposure
12. UI render
13. User override layer
14. Tests
15. Debug/admin evidence view

#### Tests required
- Unit: bedroom rules, bathroom rules, property type resolution, confidence scoring, source priority, override handling, explanation text
- Integration: authoritative data only / partial data / conflicting data / almost no data / user override / range-based estimate
- Edge cases: flat vs maisonette, end vs mid terrace, bungalow false positives, converted property, no EPC + no listing

---

### 3. Motivated Seller Signal Layer *(moved to Phase 2)*
**Source**: Conversation — competitor analysis vs Property Filter
**Priority**: Medium-High — directly addresses gap vs Property Filter

Add the following data signals to AssetLens, used as **intelligence inputs** (scoring + map layers) rather than deal-hunting triggers.

#### 3a. Sales Fallen Through
- Flag properties where sale has collapsed
- Feed into AI Deal Score as distress indicator (higher negotiation potential)
- Surface as filterable signal on Properties page
- **Source**: PropertyData status change tracking

#### 3b. Price Reduction Tracking
- Full reduction trajectory — number of cuts, period, total % dropped
- Not just a "reduced" flag — show the full history
- Feed into Deal Score as a compounding signal
- Display on Property Detail as a timeline
- **Source**: PropertyData price history endpoints (partially wired already)

#### 3c. Long-Listed Properties
- Time-on-market as a first-class scoring input
- Configurable threshold (e.g. 90 days, 180 days)
- Compound scoring: long-listed + price reductions + poor EPC = elevated distress score
- **Source**: PropertyData / listing date tracking

#### 3d. Heat Maps — Intelligence Layers
Asset Lens heat maps go beyond Property Filter's single-signal approach. Planned layers:
- Average yield by postcode
- Price reduction density
- EPC band distribution
- Deal Score averages
- Long-listed property concentration

> **Note**: These signals are used differently to Property Filter. PF uses them to say "contact this vendor." Asset Lens uses them to say "here is what the data tells you about this property and this market." Different audience, different use case.

#### Implementation notes
- Check which PropertyData endpoints are already active vs need new wiring
- Signals feed the existing `scoring_service.py` — extend the composite score model
- New filter options on the Properties page
- New map layer toggles on heat map view

---

### 4. Advertising Bar
**Source**: Conversation — revenue infrastructure  
**Priority**: Medium — revenue-ready hook, low build cost

#### What it is
A thin, fixed viewport-sticky bar pinned to the bottom of the browser window at all times, displaying a single configurable advertisement. Advertising is always property-sector relevant — conveyancing solicitors, builders, bridging finance, auction houses, estate agents, deal finders, investors, and similar. No off-topic advertising.

#### Design intent
Inconspicuous but always present. Small enough that users don't resent it; relevant enough that most will actually want to see it. This is not a pop-up. It does not interrupt. It sits quietly at the bottom and is there when needed.

#### Phase 1 scope — Single slot, manually configured
- One advertiser at a time
- Config updated manually (admin/backend) when advertiser changes
- No rotation, no scheduling, no self-serve portal

#### Layout — Logo / Text / CTA (left / centre / right)
```
[ LOGO ]   Bridging finance from 0.49% per month   [ Get a Quote → ]
```
- **Left**: Advertiser logo image
- **Centre**: Single strapline (short — see character guidance below)
- **Right**: CTA button — URL link only (Phase 1)
- **Background**: Advertiser-supplied background image (see image spec below)

The advertiser controls: logo, strapline text, CTA label, CTA URL, background image.  
They control nothing else — layout, sizing, font, and positioning are fixed by the platform.

#### Dimensions
- **Height**: 40px fixed
- **Width**: 100% viewport width
- **Position**: `position: fixed; bottom: 0; left: 0; z-index: [above all content]`
- Always on — no dismiss, no close button. Paying advertisers get persistent placement.

#### Body padding offset
The main page layout must add `padding-bottom: 40px` (or equivalent) to ensure no real page content — including footer links, copyright notice, policy links, or GeekyBee credit — is obscured by the ad bar. The footer sits above the ad bar in the normal document flow. The ad bar is a separate fixed layer beneath everything else in the UI stack.

#### Responsive image spec
Claude Code should inspect the existing codebase to confirm the Tailwind (or equivalent) breakpoint pixel widths in use, then define the background image sizes accordingly. The following is a guide — adjust to match actual breakpoints found:

| Breakpoint | Approx width | Image dimensions | Ratio |
|---|---|---|---|
| Mobile | ~375–767px | 768 × 40px | ~19:1 |
| Tablet | ~768–1023px | 1024 × 40px | ~26:1 |
| Notebook | ~1024–1279px | 1280 × 40px | ~32:1 |
| Desktop | ~1280px+ | 1920 × 40px | 48:1 |

> **Instruction for Claude Code**: Before implementing, check the project's Tailwind config (or CSS breakpoint definitions) for the actual `sm`, `md`, `lg`, `xl`, `2xl` pixel values. Use those to define the canonical image sizes and document them as comments in the component. Supply the above as a starting-point guide only.

Background image is served via `<picture>` with `srcset` / `media` attributes so the correct size loads per device. Fallback to a solid background colour if no image is supplied.

#### Strapline text guidance
- Maximum ~70 characters (fits comfortably at desktop)
- On mobile, consider truncating with ellipsis or reducing font size — Claude Code to decide best approach given 40px height constraint
- Single line only — no wrapping

#### CTA button (Phase 1)
- Action type: URL link only
- Opens in new tab (`target="_blank" rel="noopener noreferrer"`)
- Button style: platform-defined (consistent with Asset Lens UI — not advertiser-styled)
- Label: advertiser-supplied, max ~20 characters

#### Data model (Phase 1)
```json
{
  "enabled": true,
  "advertiser_name": "Example Finance Ltd",
  "strapline": "Bridging finance from 0.49% per month",
  "cta_label": "Get a Quote",
  "cta_url": "https://example.com/assetlens",
  "cta_action_type": "url",
  "logo_url": "https://cdn.assetlens.geekybee.net/ads/logo.png",
  "background_image_mobile": "https://cdn.assetlens.geekybee.net/ads/bg-mobile.jpg",
  "background_image_tablet": "https://cdn.assetlens.geekybee.net/ads/bg-tablet.jpg",
  "background_image_notebook": "https://cdn.assetlens.geekybee.net/ads/bg-notebook.jpg",
  "background_image_desktop": "https://cdn.assetlens.geekybee.net/ads/bg-desktop.jpg",
  "background_colour_fallback": "#1a1a2e",
  "text_colour": "#ffffff"
}
```

> `cta_action_type` is included now so the data model is forward-compatible. Phase 1 only implements `"url"`. Phase 2+ can add `"email"` and `"form"` without a schema change.

#### Backend
- Single config record in DB or a JSON config file — Claude Code to decide which fits better with the existing architecture
- Admin endpoint to read/update config
- No complex auth required for Phase 1 — internal update only
- `enabled: false` completely removes the bar and the bottom padding offset from the UI

#### What is NOT in Phase 1
- Multiple advertisers / rotation
- Time-based scheduling
- Impression / click tracking
- Self-serve advertiser portal
- Email or form CTA action types

These belong in the Phase 2 ad platform feature if the revenue model warrants it.

---

## Phase 1 — Delivery Sequence

Suggested order of work:

1. **Bug fixes** — clear known errors first, product must be clean before anything else
2. **Advertising bar** — quick win, revenue infrastructure in place early
3. **Motivated seller signals** — extend existing PropertyData integration
4. **Property Attribute Estimation Engine** — largest item, most impactful differentiator

---

## Phase 2 (Funding-Dependent)

The following are scoped for Phase 2 once development funding is confirmed:

- **Motivated Seller Signal Layer** — price reduction tracking, sales fallen through, long-listed properties, heat map intelligence layers
- **Property Attribute Estimation Engine** — estimates bedrooms, floor area, property type with confidence scoring and source traceability (full spec in `ASSETLENS_PROPERTY_ATTRIBUTE_ESTIMATION_BUILD_SPEC.md`)
- Multi-advertiser ad slot system with rotation and impression tracking
- Full ML pipeline for property attribute estimation (satellite imagery, title plan OCR)
- HMO suitability scoring module
- Direct-to-vendor outreach tools
- Off-market property sourcing
- User account tiers / subscription model
- Mobile app
- Portfolio management tools
- Planning history integration
- Auction data expansion

---

## Pre-Go-Live Infrastructure Checklist

Tasks to complete before the platform is considered production-ready for external users:

- [ ] **Hetzner: Add 128 GB volume to primary Coolify server** — The current Coolify instance runs on an 80 GB primary disk. As Land Registry, EPC, and scraped data volumes grow this will become a bottleneck. A 128 GB block storage volume should be attached and the Docker data directory migrated onto it (as already done on the second Coolify server). Not urgent for Phase 1 internal use, but must be completed before go-live with real users.

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| `PROGRESS.md` | Full record of completed Phases 1–7 |
| `ASSETLENS_PROPERTY_ATTRIBUTE_ESTIMATION_BUILD_SPEC.md` | Detailed build spec for estimation engine |
| This document | Phase 1 roadmap — pre-funding work |

---

*This document should be updated as bugs are identified and Phase 1 items are completed. Phase 2 scoping begins once funding is confirmed.*
