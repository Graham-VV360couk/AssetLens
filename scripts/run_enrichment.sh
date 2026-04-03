#!/bin/bash
# Re-enrich all properties with latest neighbourhood data
# Run after any data import (crime, schools, etc.) or on demand
set -e

cd /app
echo "$(date): Starting property enrichment..."
python -m backend.services.neighbourhood_service --all
echo "$(date): Enrichment complete."
