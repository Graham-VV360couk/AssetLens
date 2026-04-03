#!/bin/bash
# Monthly Land Registry Price Paid Data refresh
# Downloads current year's PPD file and upserts new transactions
# Run via cron on the 5th of each month at 4:00 AM UTC
set -e

cd /app
YEAR=$(date +%Y)
echo "$(date): Starting Land Registry refresh for $YEAR..."
python -m backend.etl.land_registry_importer --start-year $YEAR --end-year $YEAR
echo "$(date): Land Registry refresh complete."
