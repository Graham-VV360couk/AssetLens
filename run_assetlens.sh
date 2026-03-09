#!/bin/bash
# AssetLens deploy script — rebuilds both API and frontend
# Reads secrets from /opt/assetlens/.env.server (not in git)

set -e
cd "$(dirname "$0")"

# ── Backend ──────────────────────────────────────────────────
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

echo "[$(date)] API container started. Logs:"
sleep 3
docker logs assetlens-api --tail 6

# ── Frontend ─────────────────────────────────────────────────
echo "[$(date)] Building assetlens-frontend image..."
docker build -t assetlens-frontend -f docker/Dockerfile.frontend.prod .

echo "[$(date)] Restarting assetlens-frontend container..."
FRONT_LABELS=$(docker inspect assetlens-frontend --format '{{range $k,$v := .Config.Labels}}--label {{$k}}={{$v}} {{end}}' 2>/dev/null || true)
docker stop assetlens-frontend 2>/dev/null || true
docker rm assetlens-frontend 2>/dev/null || true

docker run -d \
  --name assetlens-frontend \
  --network coolify \
  --label "traefik.enable=true" \
  --label "traefik.http.routers.assetlens-front.rule=Host(\`assetlens.geekybee.net\`)" \
  --label "traefik.http.routers.assetlens-front.entrypoints=https" \
  --label "traefik.http.routers.assetlens-front.tls=true" \
  --label "traefik.http.routers.assetlens-front.tls.certresolver=letsencrypt" \
  --label "traefik.http.routers.assetlens-front.priority=10" \
  --label "traefik.http.services.assetlens-front.loadbalancer.server.port=80" \
  assetlens-frontend

echo "[$(date)] Frontend container started."
