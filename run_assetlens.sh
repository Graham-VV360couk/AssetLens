#!/bin/bash
docker stop assetlens-api 2>/dev/null
docker rm assetlens-api 2>/dev/null
docker run -d \
  --name assetlens-api \
  --network coolify \
  -p 8001:8000 \
  -e DATABASE_URL="postgres://postgres:qAR4w5va0tQXif9DsuvKvZmLn6b9811l9IATXMclHihrNCw4q3t2p29HEjC3Cg2w@q4oo8804s0gcwg4kgwccgc4k:5432/assetlens" \
  -e REDIS_URL="redis://:GpeMTijfpYfxAQiN5vJh6V3WG85Mb93lxO9jmaRZb47dsY0uvLeL75rOOtoooqyO@eo4gs04g4k0okggwgok0wg0k:6379/0" \
  -e CORS_ORIGINS="http://159.69.153.234,https://assetlens.geekybee.net,https://assetlens-api.geekybee.net" \
  -e DEBUG=false \
  -e LOG_LEVEL=INFO \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  -e ALERT_SCORE_THRESHOLD=70 \
  -e ARCHIVE_AFTER_DAYS=180 \
  -e ML_MODEL_PATH=/app/models/valuation_model.pkl \
  --label "traefik.enable=true" \
  --label 'traefik.http.routers.assetlens-api.rule=Host(`assetlens-api.geekybee.net`)' \
  --label "traefik.http.routers.assetlens-api.entrypoints=https" \
  --label "traefik.http.routers.assetlens-api.tls=true" \
  --label "traefik.http.routers.assetlens-api.tls.certresolver=letsencrypt" \
  --label "traefik.http.services.assetlens-api.loadbalancer.server.port=8000" \
  assetlens-backend
