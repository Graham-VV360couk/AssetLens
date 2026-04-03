#!/bin/bash
# Run personalised alert matching for all users
# Sends emails for new property matches above each user's threshold
set -e

cd /app
echo "$(date): Running alert matching..."
python -c "
from backend.models.base import SessionLocal
from backend.services.alert_matcher import run_daily_alerts
db = SessionLocal()
run_daily_alerts(db)
db.close()
"
echo "$(date): Alert matching complete."
