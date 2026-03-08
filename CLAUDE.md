# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AssetLens is a UK property investment intelligence dashboard that identifies, tracks, and evaluates property listings for investment potential. The system aggregates data from multiple sources (auctions, estate agents, Land Registry), analyzes historical trends, estimates market values, calculates rental yields, and alerts users to high-potential investment opportunities.

## Architecture

### Planned Tech Stack

- **Frontend**: React with Tailwind CSS and Chart.js for visualizations
- **Backend**: Python (FastAPI or Flask)
- **Database**: PostgreSQL or DragonflyDB
- **Scheduler**: Apache Airflow or Cron for ETL jobs
- **Scraping**: Scrapy with Playwright for JavaScript-heavy sites
- **Hosting**: AWS/GCP Hybrid architecture

### Core Database Schema

The system uses a relational database with the following key entities:

- **Properties**: Core property records (id, address, postcode, type, beds, source, date_found)
- **Sales History**: Historical Land Registry data (property_id, sale_date, sale_price)
- **Rentals**: Rental listings (property_id, rent_monthly, date_listed)
- **HMO Register**: HMO licensing data (property_id, licence_start, num_rooms)
- **Auctions**: Auction properties (property_id, guide_price, sold_price, auction_date)

Properties are archived after 6 months unless re-listed.

## Data Sources & Compliance

### Licensed/Allowed Sources
- **Land Registry Price Paid Data**: Open Government Licence v3.0 - requires attribution
- **HMO Registers**: Public council data - can be accessed via Searchland API or directly

### Restricted Sources
- **Rightmove/Zoopla**: No scraping allowed - must license data feeds or use Searchland/PropertyData as proxy
- **Estate Agent Sites**: Check robots.txt and terms of service before scraping

### Key APIs
- Land Registry Price Paid Data (CSV downloads)
- Searchland/PropertyData (for licensed property feeds)
- SpareRoom (rental room listings)
- OpenRent/ONS (rental trends)

## Key Features

### AI & Analytics Engine
- **Valuation Model**: Estimates market value using historical local sales data (10-year lookback)
- **Price Classification**: Categorizes properties as brilliant/good/fair/bad based on asking vs. estimated price
- **Yield Calculation**: `gross_yield = (monthly_rent × 12) / price`
- **Trend Analysis**: Detects area growth patterns from historical sales curves
- **ML Techniques**: Regression/boosting for price estimation, NLP for auction pack analysis, clustering for area segmentation

### Dashboard Requirements
- Search and filter properties by area, type, and value
- Display asking price vs. estimated market value
- Show 10-year sales history with charts
- Calculate and display rental yield and HMO opportunity scores
- Mark properties as "Reviewed" to suppress re-checking for 6 months
- Daily email alerts for high-potential properties

## Development Commands

### ETL & Data Ingestion
```bash
# Schedule daily ETL jobs (via Airflow or cron)
# Jobs should run in this order:
# 1. Land Registry data download and import
# 2. Estate agent scraping
# 3. Auction data collection
# 4. Rental data scraping
# 5. Valuation and scoring calculations
```

### Scraping Guidelines
- Always respect robots.txt and site terms of service
- Implement rate limiting and polite crawling delays
- Use rotating user agents and proxy rotation if permitted
- Store raw scraped data before processing for audit trails
- Log all scraping activities with timestamps and sources

## Data Retention Policy

- Active listings: Retained while available on source sites
- Historical data: Minimum 10 years for Land Registry sales
- Property records: Archived after 6 months of inactivity
- Scraped data: Retain for compliance auditing
- Personal data: Do not store PII beyond public advertisement content

## Configuration

The `.env` file should contain:
- Database connection strings
- API keys for data providers (Searchland, PropertyData, etc.)
- Email/SMTP settings for daily alerts
- Scraping rate limits and proxy configurations
- AI/ML model endpoints if using external services

## Next Implementation Steps

1. Set up database schema and migrations
2. Build Land Registry CSV importer (10 years of historical data)
3. Implement minimum viable scrapers for estate agent sites and auctions
4. Develop valuation model using historical sales comparables
5. Create REST API endpoints for property queries
6. Build React dashboard with search, filters, and visualization
7. Implement scoring algorithm (price differential + yield + area trends)
8. Add email alerting system for daily high-potential property notifications
9. Implement archival rules and 6-month re-check suppression
