# AssetLens

UK Property Investment Intelligence Dashboard - Identify, track, and evaluate property listings for investment potential across the entire UK.

## Overview

AssetLens aggregates data from multiple sources (licensed property feeds, auctions, estate agents, Land Registry), analyzes historical trends, estimates market values, calculates rental yields, and alerts users to high-potential investment opportunities.

## Features

- **Nationwide Coverage**: Track properties across all UK postcodes
- **Multi-Source Aggregation**: Licensed feeds (Rightmove, Zoopla, OnTheMarket via Searchland/PropertyData) + auction data
- **ML-Powered Valuation**: Estimate market values using 10 years of Land Registry historical data
- **Investment Scoring**: Composite score based on price deviation, rental yield, and area trends
- **Automatic Deduplication**: Fuzzy matching to merge properties across multiple sources
- **Daily Email Alerts**: Notifications for high-potential properties (score >70)
- **Interactive Dashboard**: Search, filter, and visualize property opportunities
- **HMO Analysis**: Identify HMO licensing opportunities

## Tech Stack

- **Frontend**: React 18 + Tailwind CSS + Chart.js
- **Backend**: Python FastAPI
- **Database**: PostgreSQL 15 (optimized for nationwide scale)
- **Cache**: Redis
- **Scraping**: Scrapy + Playwright
- **ML**: XGBoost/LightGBM for valuation
- **Orchestration**: Docker Compose

## Project Status

### ✅ Completed (Phase 1: Foundation)

1. Project directory structure
2. Environment configuration (.env.example, .gitignore)
3. Python backend dependencies (requirements.txt)
4. Complete database models (SQLAlchemy):
   - Properties
   - PropertySources (multi-source tracking)
   - PropertyScores (investment scoring)
   - SalesHistory (Land Registry data)
   - Rentals (yield calculations)
   - HMORegister (licensing data)
   - Auctions
5. Database migrations (Alembic) with optimized indexes
6. Docker Compose development environment (PostgreSQL, Redis, backend, frontend)

### 🔨 In Progress

- Land Registry data importer
- Searchland/PropertyData API client
- Property deduplication service

### 📋 Planned

- Auction scrapers
- Rental data collection
- ML valuation model
- Scoring algorithm
- REST API endpoints
- React dashboard
- Email alerts
- Archival system

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- API keys for Searchland/PropertyData (for licensed property feeds)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AssetLens
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys and configuration
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - PgAdmin (optional): http://localhost:5050

### Development Workflow

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after changes
docker-compose up -d --build

# Run backend shell
docker-compose exec backend bash

# Run database migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
```

## Project Structure

```
assetlens/
├── backend/
│   ├── api/                 # FastAPI application
│   ├── scrapers/            # Scrapy spiders
│   ├── models/              # SQLAlchemy ORM models ✅
│   ├── services/            # Business logic
│   ├── ml/                  # Valuation models
│   ├── etl/                 # Data pipeline jobs
│   ├── requirements.txt     # Python dependencies ✅
│   └── alembic.ini          # Database migration config ✅
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Dashboard pages
│   │   ├── services/        # API clients
│   │   └── utils/           # Helper functions
│   └── package.json         # Node.js dependencies
├── database/
│   ├── migrations/          # Alembic migrations ✅
│   └── seeds/               # Test data
├── docker/
│   ├── Dockerfile.backend   # Backend container ✅
│   └── Dockerfile.frontend  # Frontend container ✅
├── tests/                   # Test suite
├── .env.example             # Environment template ✅
├── .gitignore               # Git ignore rules ✅
├── docker-compose.yml       # Docker orchestration ✅
└── CLAUDE.md                # Project guidance for Claude Code ✅
```

## Database Schema

### Core Tables

- **properties**: Core property records with address, type, price, status
- **property_sources**: Multi-source tracking (Searchland, auctions, etc.)
- **property_scores**: Investment scores and valuations
- **sales_history**: Land Registry 10-year historical data (5M+ records)
- **rentals**: Rental listings for yield calculations
- **hmo_registers**: HMO licensing data by council
- **auctions**: Auction property listings

### Key Indexes

Optimized for nationwide queries:
- Postcode + type + status (composite)
- Investment score (DESC)
- Sale date + postcode
- Review status + date

## Data Sources

### Licensed Feeds (Primary)
- **Searchland/PropertyData**: Rightmove, Zoopla, OnTheMarket (requires API key)
- **Land Registry**: Price Paid Data (Open Government Licence v3.0)

### Supplementary (Scraping)
- **Auctions**: PropertyAuctions.io, Savills, Allsop
- **Rentals**: SpareRoom, OpenRent

## Configuration

See `.env.example` for full configuration options:

### Required
- `DB_*`: PostgreSQL connection
- `SEARCHLAND_API_KEY`: Licensed property feed access
- `SMTP_*`: Email alert configuration

### Optional
- `REDIS_*`: Cache configuration
- `SENTRY_DSN`: Error tracking
- `FEATURE_*`: Feature flags

## API Endpoints (Planned)

```
GET  /api/properties              # Search & filter properties
GET  /api/properties/{id}         # Property details
GET  /api/properties/{id}/sales   # Sales history
POST /api/properties/{id}/review  # Mark as reviewed
GET  /api/properties/alerts       # High-potential alerts
GET  /api/areas/{postcode}/trends # Area analytics
```

## ETL Jobs (Planned)

Scheduled via cron:

```
02:00 UTC - Licensed feed import (daily)
03:00 UTC - Auction scraping (daily)
04:00 UTC - Property scoring (daily)
06:00 UTC - Email alerts (daily)
01:00 UTC Mon - Rental data (weekly)
01:00 UTC Sun - Archival job (weekly)
```

## Performance

### Database Sizing (Nationwide)
- Active properties: ~500K listings × 2KB = 1GB
- Sales history (10yr): ~5M records × 500B = 2.5GB
- Rentals: ~200K records × 500B = 100MB
- Scores: ~500K records × 300B = 150MB
- **Total**: ~4GB + indexes (~6-8GB)

### Optimizations
- PostgreSQL connection pooling (20 connections)
- Redis caching (1hr TTL for API responses)
- Batch processing (1,000 properties at a time)
- Composite indexes on common query patterns

## Legal & Compliance

### Data Attribution
- Land Registry data: © Crown copyright and database right 2026 (OGL v3.0)
- Licensed feeds: Data licensed from Searchland/PropertyData
- All attributions displayed in dashboard footer

### Data Retention
- Active listings: Retained while available
- Historical sales: Minimum 10 years
- Archived properties: 6 months of inactivity
- Reviewed properties: Suppressed for 6 months

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]

## Contact

[Add contact information here]

---

**Note**: This project requires licensed property data feeds (Searchland or PropertyData) for comprehensive coverage. Contact these providers for API access and pricing.
