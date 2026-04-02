# Asset Lens — Addendum Amendment 001

**Amends:** asset_lens_addendum.md  
**Section affected:** New section — insert before Section A  
**For:** Claude VSCode  
**Status:** Confirmed spec

---

## Pricing & Tier Structure (Full Reference)

This section was missing from the addendum. It defines all subscription tiers, access rights, and the Stripe gating logic. Treat this as the authoritative reference for all auth and billing work in Sprint 2 and Sprint 3.

### Tier definitions

| Tier | Monthly | Annual | Who |
|---|---|---|---|
| Public visitor | Free | — | No account required |
| Free trial | Free | — | Account created, trial limits apply |
| Investor | £99/mo | £990/yr | Buyers, BTL investors, developers evaluating deals |
| Auction House | £55/mo | £550/yr | Auction houses listing lots |
| Deal Source | £55/mo | £550/yr | Property sourcers listing deals |
| White Label | £199/mo | £1,990/yr | Auction houses or deal sources wanting branded public pages |
| Admin | Internal | — | GeekyBee staff only |

### What each tier can do

| Feature | Public | Free trial | Investor | Auction House | Deal Source | White Label | Admin |
|---|---|---|---|---|---|---|---|
| View public listing pages | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Partial address / district postcode | ✓ | ✓ | — | — | — | — | — |
| Full address + postcode | — | ✓ (trial limit) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Max 3 photos (public view) | ✓ | ✓ | — | — | — | — | — |
| All photos + floor plan | — | ✓ (trial limit) | ✓ | ✓ | ✓ | ✓ | ✓ |
| AI deal score | — | ✓ (trial limit) | ✓ | — | — | — | ✓ |
| Personalised deal score | — | — | ✓ | — | — | — | ✓ |
| AVM / valuation estimate | — | ✓ (trial limit) | ✓ | — | — | — | ✓ |
| Yield calculation | — | ✓ (trial limit) | ✓ | — | — | — | ✓ |
| Full EPC detail modal | — | ✓ (trial limit) | ✓ | — | — | — | ✓ |
| Comparable sold prices | — | ✓ (trial limit) | ✓ | — | — | — | ✓ |
| Planning history | — | ✓ (trial limit) | ✓ | — | — | — | ✓ |
| Flood risk / constraints | — | ✓ (trial limit) | ✓ | — | — | — | ✓ |
| Investor financial profile | — | — | ✓ | — | — | — | ✓ |
| Wharf Financial funding quote | — | — | ✓ | — | — | — | ✓ |
| Upload auction lots (CSV + form) | — | — | — | ✓ | — | ✓ | ✓ |
| Upload sourced deals (CSV + form) | — | — | — | — | ✓ | ✓ | ✓ |
| Public listing page at `/listings/auction/{username}` | — | — | — | ✓ | — | ✓ | ✓ |
| Public listing page at `/listings/deal/{username}` | — | — | — | — | ✓ | ✓ | ✓ |
| Branded public page (logo, colours, no AssetLens branding) | — | — | — | — | — | ✓ | ✓ |
| Custom subdomain (`listings.{theirdomain}.com`) | — | — | — | — | — | ✓ | ✓ |
| Configure form field visibility | — | — | — | ✓ | ✓ | ✓ | ✓ |
| User management | — | — | — | — | — | — | ✓ |
| Data Sources / scrapers page | — | — | — | — | — | — | ✓ |

### Free trial limits

A new account starts on the free trial. No credit card required at signup. Trial ends when either limit is hit — whichever comes first.

| Limit | Value |
|---|---|
| Property views (full detail) | 3 |
| AI score views | 3 |
| Days since signup | No time limit — trial is view-count gated only |

On hitting either limit, show a hard paywall prompt. User must select Investor, Auction House, or Deal Source plan and complete Stripe checkout before proceeding.

**Note:** Trial users see enriched data (AI score, AVM, EPC detail) so they experience the product's value before being asked to pay. Trial is not a degraded view — it is full access with a view counter.

### Role selection at signup

Users choose their role during registration. The role selector must offer:

- **I want to evaluate properties** → Investor (£99/mo)
- **I represent an auction house** → Auction House (£55/mo)
- **I source properties for investors** → Deal Source (£55/mo)

A user may hold both Investor and an uploader role simultaneously (e.g. a deal source who also wants to evaluate other properties). In this case they pay both subscription fees and the account has combined permissions. Stripe handles this as two separate subscriptions on the same customer ID.

### Stripe subscription gating — implementation notes

| Detail | Spec |
|---|---|
| Stripe object | One `Customer` per user. Subscriptions attached to customer. |
| Multiple roles | Two `Subscription` objects on the same `Customer` if user holds both Investor and an uploader role. |
| `subscription_status` on `users` table | Enum: `trial` / `active` / `past_due` / `cancelled`. Set by webhook. |
| `subscription_tier` on `users` table | Enum: `none` / `investor` / `auction_house` / `deal_source` / `white_label` / `admin`. Updated by webhook. |
| Access check pattern | Every protected route/component checks `subscription_status === 'active'` AND `subscription_tier` includes required role. |
| Trial access check | `subscription_status === 'trial'` AND view count below limit (stored as `trial_views_used` on `user_profiles`). |
| `past_due` behaviour | Show banner warning. Do not immediately revoke access — give 7-day grace period matching Stripe retry window. |
| `cancelled` behaviour | Revoke access immediately on webhook receipt. Show resubscribe prompt. |
| Webhook events to handle | `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed` |
| Stripe Customer Portal | Enable for self-serve plan changes, cancellation, and payment method updates. Link from account settings page. |

### Annual billing discount

Annual plans are pre-pay at 10 months' price (2 months free). The discount is reflected in the Stripe Price objects — do not implement discount logic in application code.

| Tier | Monthly | Annual (billed upfront) | Saving |
|---|---|---|---|
| Investor | £99/mo | £990/yr | £198 |
| Auction House | £55/mo | £550/yr | £110 |
| Deal Source | £55/mo | £550/yr | £110 |
| White Label | £199/mo | £1,990/yr | £398 |

---

*End of Amendment 001. This section should be treated as inserted before Section A of asset_lens_addendum.md.*
