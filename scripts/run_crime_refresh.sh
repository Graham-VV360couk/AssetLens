#!/bin/bash
# Monthly crime data refresh
# Downloads latest month from data.police.uk and imports
# Run via cron on 15th of each month at 4:30 AM UTC
# (Police data is published ~mid-month for the previous month)
set -e

cd /app
YEAR=$(date +%Y)
MONTH=$(date -d "last month" +%m 2>/dev/null || date -v-1m +%m)
DATA_URL="https://data.police.uk/data/archive/${YEAR}-${MONTH}.zip"
WORK_DIR="/tmp/crime-refresh-${YEAR}-${MONTH}"

echo "$(date): Downloading crime data for ${YEAR}-${MONTH}..."
mkdir -p "$WORK_DIR"
curl -fsSL "$DATA_URL" -o "$WORK_DIR/data.zip" || { echo "Download failed — data may not be published yet"; exit 0; }

echo "$(date): Extracting..."
cd "$WORK_DIR" && unzip -q data.zip

echo "$(date): Importing..."
cd /app
python -m backend.etl.crime_importer --data-dir "$WORK_DIR"

echo "$(date): Cleaning up..."
rm -rf "$WORK_DIR"

echo "$(date): Crime refresh complete for ${YEAR}-${MONTH}"
