#!/bin/bash
# AssetLens Health Check Script (Task #22)
# Checks all services and reports status

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }

echo "AssetLens Health Check — $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# API health
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    pass "Backend API (port 8000)"
else
    fail "Backend API (port 8000) — NOT RESPONDING"
fi

# Frontend
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    pass "Frontend (port 3000)"
else
    warn "Frontend (port 3000) — not responding (may be normal in production)"
fi

# PostgreSQL
if command -v docker &>/dev/null; then
    if docker-compose -f "$PROJECT_DIR/docker-compose.yml" exec -T db pg_isready -U assetlens > /dev/null 2>&1; then
        pass "PostgreSQL"
    else
        fail "PostgreSQL — NOT READY"
    fi

    # Redis
    if docker-compose -f "$PROJECT_DIR/docker-compose.yml" exec -T redis redis-cli ping > /dev/null 2>&1; then
        pass "Redis"
    else
        fail "Redis — NOT READY"
    fi
fi

# Log file sizes
LOG_DIR="$PROJECT_DIR/logs"
if [ -d "$LOG_DIR" ]; then
    TOTAL=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
    pass "Log directory ($TOTAL used)"
else
    warn "No log directory found"
fi

# Recent ETL run
LATEST_ETL=$(ls -t "$LOG_DIR"/etl_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_ETL" ]; then
    AGE=$(( ($(date +%s) - $(date -r "$LATEST_ETL" +%s)) / 3600 ))
    if [ "$AGE" -lt 26 ]; then
        pass "Last ETL run: ${AGE}h ago"
    else
        warn "Last ETL run: ${AGE}h ago (expected daily)"
    fi
else
    warn "No ETL logs found"
fi

echo "================================================"
echo "Done."
