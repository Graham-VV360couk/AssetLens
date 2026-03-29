#!/bin/bash
# AssetLens ETL Orchestration Script
# Run all ETL jobs in correct order
# Typically called by cron or manually

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/etl_$DATE.log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

run_job() {
    local name="$1"
    local cmd="$2"
    log "Starting: $name"
    if eval "$cmd" >> "$LOG_FILE" 2>&1; then
        log "SUCCESS: $name"
    else
        log "ERROR: $name (exit code $?)"
        return 1
    fi
}

log "=== AssetLens ETL Run Started ==="

# Run inside Docker or local Python environment
if command -v docker &>/dev/null && docker ps --filter name=assetlens_backend -q | grep -q .; then
    RUN_CMD="docker-compose -f $PROJECT_DIR/docker-compose.yml exec -T backend python"
else
    RUN_CMD="python"
    cd "$PROJECT_DIR"
fi

# Step 1: Land Registry (weekly on Mondays, skip otherwise)
if [ "$(date +%u)" = "1" ]; then
    run_job "Land Registry Import" "$RUN_CMD backend/etl/land_registry_importer.py --years 1" || true
fi

# Step 2: Licensed feed import (daily)
run_job "Licensed Feed Import" "$RUN_CMD backend/etl/licensed_feed_importer.py" || true

# Step 3: Auction scrapers (daily)
run_job "Auction Scraper" "$RUN_CMD backend/scrapers/auction_scraper.py" || true

# Step 4: Rental data (weekly on Sundays)
if [ "$(date +%u)" = "7" ]; then
    run_job "Rental Scraper" "$RUN_CMD backend/scrapers/rental_scraper.py" || true
fi

# Step 4b: Stale listing checker (weekly on Wednesdays)
if [ "$(date +%u)" = "3" ]; then
    run_job "Stale Listing Checker" "$RUN_CMD -m backend.etl.stale_listing_checker" || true
fi

# Step 5: Scoring (daily - depends on fresh data)
run_job "Daily Scoring" "$RUN_CMD backend/etl/daily_scoring_job.py" || true

# Step 6: Archival (weekly on Saturdays)
if [ "$(date +%u)" = "6" ]; then
    run_job "Archival Job" "$RUN_CMD backend/etl/archival_job.py" || true
fi

log "=== AssetLens ETL Run Complete ==="

# Clean up logs older than 30 days
find "$LOG_DIR" -name "etl_*.log" -mtime +30 -delete 2>/dev/null || true
