#!/bin/bash
# AssetLens API deploy script
# Reads secrets from /opt/assetlens/.env.server (not in git)
# Run: bash /opt/assetlens/run_assetlens.sh

set -e
cd "$(dirname "$0")"

echo "[$(date)] Building assetlens-backend image..."
docker build -t assetlens-backend .

echo "[$(date)] Restarting assetlens-api container..."
docker stop assetlens-api 2>/dev/null || true
docker rm assetlens-api 2>/dev/null || true

docker run -d \
  --name assetlens-api \
  --network coolify \
  -p 8001:8000 \
  --env-file /opt/assetlens/.env.server \
  assetlens-backend

echo "[$(date)] Container started. Logs:"
sleep 3
docker logs assetlens-api --tail 8
