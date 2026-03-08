# ============================================================
# AssetLens Backend — Production Dockerfile
# Multi-stage: builder installs deps, final image is slim
# ============================================================

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim AS runtime

LABEL maintainer="AssetLens" \
      description="UK Property Investment Intelligence API" \
      version="1.0.0"

WORKDIR /app

# Install runtime system deps only (libpq5 for psycopg2, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder (system-wide, no --user)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/
COPY database/ ./database/
COPY scripts/ ./scripts/

# Create required runtime directories
RUN mkdir -p /app/logs /app/models

# Non-root user for security
RUN groupadd -r assetlens && useradd -r -g assetlens -d /app assetlens \
    && chown -R assetlens:assetlens /app
USER assetlens

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run migrations then start API
CMD ["sh", "-c", "python -m alembic -c backend/alembic.ini upgrade head && uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 2"]
