# AssetLens Production Deployment

This document provides quick reference for production deployment of AssetLens.

## Quick Links

- **Full Deployment Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Project Documentation**: See [CLAUDE.md](CLAUDE.md)
- **Development Setup**: See main [README.md](README.md)

## Production vs Development

AssetLens has two Docker configurations:

| File | Purpose | Use Case |
|------|---------|----------|
| `docker-compose.yml` | Development | Local development with live reload |
| `docker-compose.prod.yml` | Production | Coolify/production deployment |

### Key Differences

**Development** (`docker-compose.yml`):
- ✅ Volume mounts for live code reload
- ✅ Exposed ports for debugging (5432, 6379, 8000, 3000)
- ✅ React development server
- ✅ Hot module replacement
- ❌ Not suitable for production

**Production** (`docker-compose.prod.yml`):
- ✅ Code baked into images (no volume mounts)
- ✅ Optimized multi-stage builds
- ✅ Nginx serving static files + reverse proxy
- ✅ Only frontend exposed (ports 80/443)
- ✅ Production-grade security
- ✅ Health checks and restart policies

## Quick Start for Production

### 1. Prerequisites

- Coolify instance or Docker host
- Domain name configured
- Minimum 4GB RAM, 2 vCPUs

### 2. Configure Environment

```bash
# Copy template
cp .env.production .env

# Edit with your values
nano .env

# Required values:
# - DB_PASSWORD
# - SECRET_KEY
# - SMTP_PASSWORD
# - CORS_ORIGINS
```

### 3. Test Locally (Optional)

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check health
curl http://localhost/health

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop when done
docker-compose -f docker-compose.prod.yml down
```

### 4. Deploy to Coolify

1. Create new Docker Compose service in Coolify
2. Upload `docker-compose.prod.yml`
3. Add environment variables from `.env`
4. Configure domain: `assetlens.yourdomain.com`
5. Enable SSL (Let's Encrypt)
6. Click Deploy

### 5. Verify Deployment

```bash
# Health check
curl https://assetlens.yourdomain.com/health

# API docs
curl https://assetlens.yourdomain.com/docs

# Frontend
open https://assetlens.yourdomain.com
```

## Production Architecture

```
┌─────────────────────────────────────┐
│         Internet (HTTPS)            │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│    Coolify / Load Balancer          │
│    (SSL Termination)                │
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Frontend Container (Nginx)         │
│  - Serve React app                  │
│  - Reverse proxy /api → backend     │
│  Ports: 80, 443                     │
└─────────────┬───────────────────────┘
              ↓ /api
┌─────────────────────────────────────┐
│  Backend Container (FastAPI)        │
│  - REST API                         │
│  - Internal port 8000               │
└──────┬──────────────┬───────────────┘
       ↓              ↓
┌─────────────┐  ┌──────────┐
│ PostgreSQL  │  │  Redis   │
│ (Internal)  │  │ (Internal)│
└─────────────┘  └──────────┘
```

## File Structure

```
AssetLens/
├── docker/
│   ├── Dockerfile.backend.prod      # Production backend
│   ├── Dockerfile.frontend.prod     # Production frontend
│   ├── Dockerfile.backend           # Development backend
│   └── Dockerfile.frontend          # Development frontend
├── nginx/
│   ├── frontend.conf                # Nginx site config
│   └── nginx.conf                   # Nginx main config
├── docker-compose.prod.yml          # Production orchestration
├── docker-compose.yml               # Development orchestration
├── .env.production                  # Production env template
├── DEPLOYMENT.md                    # Full deployment guide
└── README.production.md             # This file
```

## Common Commands

### Local Testing

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Check service health
docker-compose -f docker-compose.prod.yml ps

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Production Management

```bash
# View logs (via Coolify or direct)
docker logs assetlens_backend_1 --tail 100

# Restart service
docker restart assetlens_backend_1

# Database backup
docker exec assetlens_postgres_1 pg_dump -U postgres assetlens > backup.sql

# Run migrations
docker exec assetlens_backend_1 alembic upgrade head

# Access backend shell
docker exec -it assetlens_backend_1 bash

# Access database
docker exec -it assetlens_postgres_1 psql -U postgres assetlens
```

## Scheduled Jobs

Configure cron jobs for data processing:

```bash
# Daily data import (2 AM)
0 2 * * * docker exec assetlens_backend_1 python /app/backend/etl/land_registry_importer.py

# Daily scraping (3 AM)
0 3 * * * docker exec assetlens_backend_1 python /app/backend/scrapers/run_all_scrapers.py

# Daily scoring (4 AM)
0 4 * * * docker exec assetlens_backend_1 python /app/backend/etl/daily_scoring_job.py

# Daily alerts (6 AM)
0 6 * * * docker exec assetlens_backend_1 python /app/backend/services/send_daily_alerts.py
```

## Environment Variables

### Essential

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_PASSWORD` | PostgreSQL password | Random 32-char string |
| `SECRET_KEY` | JWT secret | `openssl rand -hex 32` |
| `CORS_ORIGINS` | Allowed domains | `https://yourdomain.com` |

### Optional but Recommended

| Variable | Description | Default |
|----------|-------------|---------|
| `SEARCHLAND_API_KEY` | Property data API | - |
| `SMTP_PASSWORD` | Email service key | - |
| `FEATURE_EMAIL_ALERTS` | Enable alerts | `true` |
| `FEATURE_ML_VALUATION` | Enable ML | `true` |

See `.env.production` for complete list.

## Security Checklist

Before production deployment:

- [ ] Change `DB_PASSWORD` to secure value
- [ ] Generate unique `SECRET_KEY`
- [ ] Set `CORS_ORIGINS` to your domain only
- [ ] Configure `SMTP_PASSWORD` for SendGrid
- [ ] Enable HTTPS/SSL via Coolify
- [ ] Restrict database to internal network
- [ ] Set up automated backups
- [ ] Configure firewall rules
- [ ] Review nginx security headers
- [ ] Enable rate limiting (future)

## Monitoring

### Health Checks

All services have health checks:

- **Backend**: `http://backend:8000/health`
- **PostgreSQL**: `pg_isready`
- **Redis**: `redis-cli ping`
- **Frontend**: `wget http://localhost/`

### Logs

Access via Coolify dashboard or:

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Application logs
docker exec assetlens_backend_1 tail -f /app/logs/app.log
```

### Metrics

Monitor in Coolify:
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

## Backup Strategy

### Daily Automated Backups

```bash
#!/bin/bash
# /etc/cron.daily/assetlens-backup

BACKUP_DIR="/backups/assetlens"
DATE=$(date +%Y%m%d)

# Database
docker exec assetlens_postgres_1 pg_dump -U postgres assetlens | \
  gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Redis
docker exec assetlens_redis_1 redis-cli SAVE
docker cp assetlens_redis_1:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Cleanup old backups (30 days)
find "$BACKUP_DIR" -mtime +30 -delete
```

### S3 Backup (Recommended)

Configure in `.env`:

```bash
BACKUP_S3_BUCKET=assetlens-backups
BACKUP_S3_REGION=eu-west-2
BACKUP_S3_ACCESS_KEY=xxx
BACKUP_S3_SECRET_KEY=xxx
```

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker logs assetlens_backend_1

# Common issues:
# - Missing environment variables
# - Database not ready
# - Port conflicts
```

### Database Connection Failed

```bash
# Verify postgres is running
docker ps | grep postgres

# Test connection
docker exec assetlens_backend_1 pg_isready -h postgres -U postgres

# Check credentials match
docker exec assetlens_backend_1 env | grep DB_
```

### Frontend Can't Reach API

```bash
# Check nginx config
docker exec assetlens_frontend_1 cat /etc/nginx/conf.d/default.conf

# Test backend from frontend
docker exec assetlens_frontend_1 wget -O- http://backend:8000/health

# Verify API URL
# Should be: REACT_APP_API_URL=/api
```

## Updating

### Via Coolify

1. Push code to Git repository
2. In Coolify, click "Redeploy"
3. Monitor build logs
4. Verify health checks pass

### Manual Update

```bash
# Pull latest code
git pull

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

## Performance Optimization

### Database

```bash
# Connection pooling
DB_POOL_SIZE=20

# Vacuum database weekly
docker exec assetlens_postgres_1 psql -U postgres assetlens -c "VACUUM ANALYZE;"
```

### Caching

```bash
# Increase cache TTL
CACHE_TTL=7200

# Increase Redis memory
# In docker-compose.prod.yml:
--maxmemory 1gb
```

### Scaling

For high traffic:

1. Add more backend workers (modify Dockerfile.backend.prod)
2. Use managed PostgreSQL (AWS RDS)
3. Add Redis cluster
4. Deploy CDN for static assets
5. Configure load balancer

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/AssetLens/issues)
- **Docs**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Development**: [CLAUDE.md](CLAUDE.md)

## License

See main README.md

---

**Quick Command Reference**

```bash
# Build production
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check health
curl http://localhost/health

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down

# Backup database
docker exec assetlens_postgres_1 pg_dump -U postgres assetlens > backup.sql
```

Ready to deploy AssetLens to production!
