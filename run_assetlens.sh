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
  -e ANTHROPIC_API_KEY="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" \
  -e OPENAI_API_KEY="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" \
  -e SMTP_HOST="smtp-relay.brevo.com" \
  -e SMTP_PORT="587" \
  -e SMTP_USERNAME="910447001@smtp-brevo.com" \
  -e SMTP_PASSWORD="xsmtpsib-52a273c1fb0c90e5d3bf82552005abfced11c454dd3e1ded06c7c1fc7ebc90d1-yz0NdIrp93tJqO2B" \
  -e SMTP_FROM_EMAIL="noreply@geekybee.net" \
  -e SMTP_FROM_NAME="AssetLens Alert" \
  -e ALERT_SCORE_THRESHOLD=70 \
  -e ARCHIVE_AFTER_DAYS=180 \
  -e ML_MODEL_PATH=/app/models/valuation_model.pkl \
  -e PROPERTYDATA_API_KEY="ZQZUPHWLJI" \
  assetlens-backend
