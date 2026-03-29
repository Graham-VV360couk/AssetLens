# Design: Advertising Bar
**Date**: 2026-03-28
**Status**: Approved
**Scope**: Phase 1 — Revenue Infrastructure

---

## Context

A sticky, fixed-position advertising bar pinned to the bottom of the viewport. Always visible, never dismissible. Property-sector advertising only (conveyancing, bridging finance, builders, auctioneers, estate agents, etc.).

Phase 1: single advertiser slot, manually approved workflow. No rotation, no impression tracking, no self-serve portal.

---

## Architecture

### Config file: `backend/ad_config.json`

Two slots: `live` (currently displayed) and `pending` (awaiting admin approval). Admin approves `pending` to replace `live`.

```json
{
  "live": {
    "enabled": true,
    "advertiser_name": "Example Finance Ltd",
    "strapline": "Bridging finance from 0.49% per month",
    "cta_label": "Get a Quote",
    "cta_url": "https://example.com/assetlens",
    "logo_url": "https://i.ibb.co/example/logo.png",
    "background_image_mobile": "https://i.ibb.co/example/bg-mobile.jpg",
    "background_image_desktop": "https://i.ibb.co/example/bg-desktop.jpg",
    "background_colour_fallback": "#1a1a2e",
    "text_colour": "#ffffff"
  },
  "pending": null
}
```

`enabled: false` removes the bar and its `padding-bottom` offset from the UI entirely. `pending: null` means no submission awaiting approval.

### Components

Three new frontend components, one new backend router:

| Component | Purpose |
|---|---|
| `frontend/src/components/ads/AdBar.jsx` | Fixed sticky bar rendered in root layout |
| `frontend/src/pages/AdSubmit.jsx` | Public submit form at `/advertise` |
| `frontend/src/pages/AdminAds.jsx` | Admin approval page at `/admin/ads` |
| `backend/api/routers/ads.py` | API: GET live config, POST submit, POST approve/reject |

---

## Ad Bar Component

### Dimensions
- **Height**: 50px fixed
- **Width**: 100% viewport width
- **Position**: `position: fixed; bottom: 0; left: 0; z-index: 9999`
- No close button. No dismiss. Paying advertisers get permanent placement.

### Layout (left / centre / right)
```
[ LOGO ]   Bridging finance from 0.49% / per month   [ Get a Quote → ]
```

- **Left**: Advertiser logo image, max height 30px, `object-contain`, left-padded
- **Centre**: Strapline — single line on desktop (`lg:text-sm`); two lines on mobile (`text-[10px] leading-tight`), truncated with ellipsis if overflows
- **Right**: CTA button — platform-styled (consistent with AssetLens UI), opens `target="_blank" rel="noopener noreferrer"`

### Background
`<picture>` element with two `<source>` entries:
- `media="(min-width: 1024px)"` → `background_image_desktop` (1920×50px)
- default → `background_image_mobile` (640×50px)

Falls back to `background_colour_fallback` (#1a1a2e) if no image supplied.

Text colour controlled by `text_colour` field.

### Responsive image spec
Tailwind breakpoints (from `frontend/tailwind.config.js`): sm:640, md:768, lg:1024, xl:1280, 2xl:1536. Two images cover the range:

| Slot | Breakpoint boundary | Dimensions | Ratio |
|---|---|---|---|
| Mobile | below lg (< 1024px) | 640 × 50px | ~13:1 |
| Desktop | lg and above (≥ 1024px) | 1920 × 50px | ~38:1 |

### Sidebar offset
The platform has a `w-64` (256px) sidebar on `lg+` screens. The ad bar must not overlap the sidebar visually. The bar itself spans full viewport width; on `lg+` the inner content container gains `lg:pl-64` to align with the main content area.

### Body padding offset
The root layout adds `pb-[50px]` when the bar is enabled, ensuring no page content (footer links, copyright, GeekyBee credit) is obscured by the fixed bar.

### Strapline guidance
- Desktop: single line, max ~80 characters
- Mobile: two lines at `text-[10px] leading-tight`, `line-clamp-2` — no wrap beyond two lines

---

## Submit & Approval Flow

### Advertiser submission — `POST /api/ads/submit`
- Protected by `AD_SUBMIT_TOKEN` bearer token (environment variable)
- Advertiser provides: `advertiser_name`, `strapline`, `cta_label`, `cta_url`, plus two image files (mobile 640×50, desktop 1920×50)
- Backend uploads each image to ImgBB using `IMGBB_API_KEY` (from environment)
- Stores populated pending slot in `backend/ad_config.json`
- Triggers email notification to admin (existing email service)
- Returns 200 on success; 409 if a pending submission already exists

### Admin approval — `POST /api/ads/approve`
- Protected by `AD_ADMIN_TOKEN` bearer token (environment variable)
- Action: `"approve"` — copies `pending` → `live`, clears `pending`, sets `enabled: true`
- Action: `"reject"` — clears `pending` only; `live` slot unchanged
- Returns current config state

### Admin page — `/admin/ads`
- Displays current live ad (if any) and pending ad side-by-side
- Shows preview of pending ad bar (inline mockup)
- Approve / Reject buttons (both call `POST /api/ads/approve` with appropriate action)
- Toggle to disable live ad entirely (`enabled: false`)
- Protected by `AD_ADMIN_TOKEN` (entered in-page, stored in `sessionStorage` — no user accounts needed for Phase 1)

### Public submission page — `/advertise`
Simple form: text fields + two file upload inputs (mobile image, desktop image) + submit token field. On success: "Your submission has been received and is awaiting approval."

### ImgBB integration
- API endpoint: `https://api.imgbb.com/1/upload`
- `IMGBB_API_KEY` stored in `.env` / environment
- Backend uploads images server-side (not from browser) to keep the API key server-only
- `ImgBBClient` utility in `backend/services/imgbb_client.py`

---

## API Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/ads/config` | None | Returns live ad config (frontend fetches this) |
| `POST` | `/api/ads/submit` | `AD_SUBMIT_TOKEN` | Advertiser submits new ad + images |
| `POST` | `/api/ads/approve` | `AD_ADMIN_TOKEN` | Admin approves or rejects pending |

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `IMGBB_API_KEY` | ImgBB upload API key |
| `AD_SUBMIT_TOKEN` | Bearer token for advertiser submission |
| `AD_ADMIN_TOKEN` | Bearer token for admin approval actions |

---

## Out of Scope (Phase 1)
- Multiple advertiser rotation
- Time-based scheduling
- Impression / click tracking
- Self-serve advertiser portal
- Email or form CTA action types
- Real authentication for admin page (token in sessionStorage is sufficient for Phase 1)
