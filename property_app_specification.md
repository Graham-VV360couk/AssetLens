# Property Investment Intelligence Dashboard (UK-Focused)

A comprehensive specification for a web-based app that identifies, tracks, and evaluates property listings in the UK for investment potential — including auctions, estate agents, and private sales — using historical price data, rental/HMO analysis, and AI valuation.

---

## 📌 Project Overview

**Goal**: Discover undervalued UK properties by:
- Aggregating live listings from portals and auctions.
- Comparing against Land Registry sales (last 10 years).
- Estimating market value and rental/HMO yield.
- Scoring investment potential.
- Alerting daily on high-potential properties.
- Storing property data for 6 months minimum.

---

## 🔗 Data Sources

### 1. Land Registry (Price Paid Data)
- Open Government Licence.
- Historical sales: address, price, date, property type.
- Use for area price trends and comparables.

### 2. Estate Listings
- Portals: Rightmove, Zoopla, OnTheMarket.
- No public API – scrape or license data feeds.
- Extract: price, address, type, features, agent.

### 3. Auction Data
- Sources: PropertyAuctions.io, Savills, Allsop.
- Fields: guide price, sold price, date, auctioneer.

### 4. Rental & HMO Data
- SpareRoom (room listings).
- OpenRent, ONS (rent trends).
- Searchland or PropertyData for national HMO register.
- Fields: rent, postcode, room count, licence date.

---

## 🔄 Data Ingestion Strategy

- Use Scrapy or BeautifulSoup for scraping.
- Schedule daily ETL jobs (e.g. via Airflow).
- Respect robots.txt & site TOS.
- Optionally license Searchland/API feeds for speed & compliance.

---

## 🧠 AI & Analytics Engine

- **Valuation**: Estimate book price using past local sales.
- **Classification**: Price banding (brilliant/good/fair/bad).
- **Yield**: Gross yield = (monthly rent × 12) / price.
- **Trend Analysis**: Detect area growth from 10-year sales curve.
- **ML Techniques**:
  - Regression/boosting for price estimation.
  - NLP for auction/legal pack insights.
  - Clustering for area segmentation.

---

## 🗃️ Database Schema (SQL)

```sql
-- Properties
id, address, postcode, type, beds, source, date_found

-- Sales History
property_id, sale_date, sale_price

-- Rentals
property_id, rent_monthly, date_listed

-- HMO Register
property_id, licence_start, num_rooms

-- Auctions
property_id, guide_price, sold_price, auction_date
```

Use DragonflyDB or Postgres. Archive properties after 6 months unless re-listed.

---

## 📊 Dashboard & Alerts

- Web-based dashboard (React or Vue).
- Search listings by area/type/value.
- Show:
  - Asking vs. estimated price
  - Sale history & 10-year chart
  - Rental yield & HMO opportunity
- Daily email alerts for high-potential properties.
- Mark as “Reviewed” to suppress re-checking for 6 months.

---

## 🧰 Suggested Tech Stack

| Layer        | Tech Choices             |
|--------------|---------------------------|
| Frontend     | React, Tailwind, Chart.js |
| Backend      | Python (FastAPI/Flask)    |
| Database     | PostgreSQL or DragonflyDB |
| Scheduler    | Airflow or Cron           |
| Scraping     | Scrapy, Playwright        |
| Hosting      | AWS/GCP Hybrid            |

---

## ⚖️ Licensing & Compliance

- ✅ **Land Registry**: OGL v3.0 — requires attribution.
- ❌ **Rightmove/Zoopla**: No scraping allowed — license or proxy via Searchland/PropertyData.
- ✅ **HMO Registers**: Public via council — or API via Searchland.
- ⚠️ Personal data: Do not store PII beyond public ad content.

---

## ✅ Summary

- Smart daily property discovery.
- Reliable price, rental, and trend insights.
- AI-assisted yield/price scoring.
- 6-month archival and re-check system.
- Hybrid cloud + SQL + modern web stack.

---

## ➕ Next Steps

1. Build minimum viable scraper for estate & auction sites.
2. Download Land Registry Price Paid CSV (last 10 years).
3. Set up SQL schema and data loader.
4. Prototype dashboard UI with filters and scoring.
5. Integrate AI/valuation logic after data validation.
6. Launch email alerting and archival rules.
