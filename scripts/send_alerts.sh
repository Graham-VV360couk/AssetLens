#!/bin/bash
# AssetLens Daily Alert Email
# Scheduled at 6 AM UTC daily

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$LOG_DIR"

if command -v docker &>/dev/null && docker ps --filter name=assetlens_backend -q | grep -q .; then
    docker-compose -f "$PROJECT_DIR/docker-compose.yml" exec -T backend \
        python backend/etl/daily_alert_job.py >> "$LOG_DIR/alerts_$DATE.log" 2>&1
else
    cd "$PROJECT_DIR"
    python backend/etl/daily_alert_job.py >> "$LOG_DIR/alerts_$DATE.log" 2>&1
fi
