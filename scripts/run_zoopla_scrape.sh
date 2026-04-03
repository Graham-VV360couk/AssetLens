#!/bin/bash
# Daily Zoopla for-sale listings scrape
# Scrapes all districts where we have active properties
# Run via cron at 3:00 AM UTC (after ETL, before scoring)
set -e

cd /app
echo "$(date): Starting Zoopla scrape..."
python -m backend.scrapers.zoopla_scraper --districts-from-db --pages 5
echo "$(date): Zoopla scrape complete."

# Re-enrich any new properties
echo "$(date): Enriching new properties..."
python -m backend.services.neighbourhood_service
echo "$(date): Enrichment complete."
