# AssetLens Coolify Deployment Guide

This guide covers deploying AssetLens to Coolify or other Docker-based hosting platforms.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Steps](#deployment-steps)
- [Configuration](#configuration)
- [Scheduled Jobs](#scheduled-jobs)
- [Monitoring](#monitoring)
- [Backup & Restore](#backup--restore)
- [Troubleshooting](#troubleshooting)
- [Updating](#updating)

## Prerequisites

### Required
- Coolify instance (v4.0+) or similar Docker hosting platform
- Domain name configured and pointing to your server
- Minimum server specs:
  - 2 vCPUs
  - 4GB RAM
  - 50GB SSD storage

### Optional but Recommended
- SendGrid account for email alerts
- Searchland or PropertyData API key for licensed data feeds
- SSL certificate (Coolify auto-generates with Let's Encrypt)

## Quick Start

For a rapid deployment:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/AssetLens.git
cd AssetLens

# 2. Copy and configure environment variables
cp .env.production .env
# Edit .env with your values

# 3. Build and test locally (optional)
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 4. Deploy to Coolify (see Deployment Steps below)
```

## Deployment Steps

### 1. Create New Service in Coolify

1. Log into your Coolify dashboard
2. Click **"New Resource"** → **"Docker Compose"**
3. Select your target server
4. Enter service details:
   - **Name**: `assetlens`
   - **Repository**: Your Git repository URL (optional if using uploaded files)

### 2. Add docker-compose.prod.yml

Copy the contents of `docker-compose.prod.yml` to Coolify's compose editor, or configure Coolify to use the file from your repository.

### 3. Configure Environment Variables

In Coolify's environment variables section, add all variables from `.env.production`:

#### Essential Variables

```bash
# Database (REQUIRED)
DB_PASSWORD=<generate-secure-password>
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Email (REQUIRED for alerts)
SMTP_PASSWORD=<your-sendgrid-api-key>
SMTP_FROM_EMAIL=alerts@yourdomain.com
ALERT_EMAIL=your@email.com

# CORS (REQUIRED)
CORS_ORIGINS=https://assetlens.yourdomain.com

# API Keys (OPTIONAL but recommended)
SEARCHLAND_API_KEY=<your-key>
PROPERTYDATA_API_KEY=<your-key>
```

#### Generate Secure Credentials

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate DB_PASSWORD
openssl rand -base64 32
```

### 4. Configure Domain

1. In Coolify, go to your service settings
2. Add domain: `assetlens.yourdomain.com`
3. Enable **SSL/TLS** (auto Let's Encrypt)
4. Save configuration

### 5. Deploy

1. Click **"Deploy"** in Coolify
2. Monitor the build logs
3. Wait for all services to become healthy (~2-5 minutes)

### 6. Verify Deployment

Check each endpoint:

```bash
# Health check
curl https://assetlens.yourdomain.com/health

# API status
curl https://assetlens.yourdomain.com/api/status

# Frontend
open https://assetlens.yourdomain.com

# API documentation
open https://assetlens.yourdomain.com/docs
```

Expected response from health check:
```json
{
  "status": "healthy",
  "service": "assetlens-api",
  "version": "1.0.0",
  "environment": "production"
}
```

## Configuration

### Environment Variables Reference

See `.env.production` for complete list. Key variables:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DB_PASSWORD` | PostgreSQL password | Yes | - |
| `SECRET_KEY` | JWT secret key | Yes | - |
| `SMTP_PASSWORD` | Email service API key | Yes* | - |
| `CORS_ORIGINS` | Allowed frontend URLs | Yes | * |
| `SEARCHLAND_API_KEY` | Property data API | No | - |
| `FEATURE_EMAIL_ALERTS` | Enable email alerts | No | true |
| `FEATURE_ML_VALUATION` | Enable ML valuations | No | true |

*Required if email alerts are enabled

### Feature Flags

Control features via environment variables:

```bash
# Disable email alerts
FEATURE_EMAIL_ALERTS=false

# Disable ML valuation model
FEATURE_ML_VALUATION=false
```

### Performance Tuning

For high-traffic deployments:

```bash
# Increase database connections
DB_POOL_SIZE=20

# Increase cache TTL
CACHE_TTL=7200

# Adjust API timeout
API_TIMEOUT=60
```

## Scheduled Jobs

AssetLens requires scheduled jobs for data ingestion and alerts.

### Option 1: Coolify Cron Jobs

Configure in Coolify's scheduled tasks:

```bash
# Daily Land Registry data import (2 AM UTC)
0 2 * * * docker exec assetlens_backend_1 python /app/backend/etl/land_registry_importer.py

# Daily property scraping (3 AM UTC)
0 3 * * * docker exec assetlens_backend_1 python /app/backend/scrapers/run_all_scrapers.py

# Daily scoring calculation (4 AM UTC)
0 4 * * * docker exec assetlens_backend_1 python /app/backend/etl/daily_scoring_job.py

# Daily email alerts (6 AM UTC)
0 6 * * * docker exec assetlens_backend_1 python /app/backend/services/send_daily_alerts.py

# Weekly data cleanup (Sunday 1 AM UTC)
0 1 * * 0 docker exec assetlens_backend_1 python /app/backend/etl/archive_old_properties.py
```

### Option 2: External Cron Service

Use a service like [cron-job.org](https://cron-job.org):

```bash
# Configure HTTP-based cron jobs
POST https://assetlens.yourdomain.com/api/jobs/import-land-registry
POST https://assetlens.yourdomain.com/api/jobs/run-scrapers
POST https://assetlens.yourdomain.com/api/jobs/calculate-scores
POST https://assetlens.yourdomain.com/api/jobs/send-alerts
```

### Verifying Job Execution

Check logs after scheduled job runs:

```bash
# View backend logs
docker logs assetlens_backend_1 --tail 100

# View specific job logs
docker exec assetlens_backend_1 cat /app/logs/etl.log
```

## Monitoring

### Health Checks

Coolify automatically monitors service health using Docker healthchecks defined in `docker-compose.prod.yml`.

### Resource Usage

Monitor in Coolify dashboard:
- CPU usage
- Memory usage
- Disk usage
- Network traffic

### Logs

Access logs via Coolify dashboard or Docker commands:

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail 100 backend

# Application logs
docker exec assetlens_backend_1 tail -f /app/logs/app.log
```

### Alerts

Configure Coolify to send notifications for:
- Service down
- High resource usage
- Failed deployments

## Backup & Restore

### Automatic Backups

Configure in Coolify or set up automated scripts:

```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR="/backups/assetlens"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL database
docker exec assetlens_postgres_1 pg_dump -U postgres assetlens | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Backup Redis data
docker exec assetlens_redis_1 redis-cli SAVE
docker cp assetlens_redis_1:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Manual Database Backup

```bash
# Export database
docker exec assetlens_postgres_1 pg_dump -U postgres assetlens > backup.sql

# Compress backup
gzip backup.sql
```

### Restore Database

```bash
# Stop backend service
docker-compose -f docker-compose.prod.yml stop backend

# Restore database
gunzip < backup.sql.gz | docker exec -i assetlens_postgres_1 psql -U postgres assetlens

# Restart backend
docker-compose -f docker-compose.prod.yml start backend
```

### S3 Backup (Recommended for Production)

Configure in `.env`:

```bash
BACKUP_S3_BUCKET=assetlens-backups
BACKUP_S3_REGION=eu-west-2
BACKUP_S3_ACCESS_KEY=your-access-key
BACKUP_S3_SECRET_KEY=your-secret-key
```

Automated S3 backup script:

```bash
#!/bin/bash
# s3-backup.sh

# Backup database
docker exec assetlens_postgres_1 pg_dump -U postgres assetlens | gzip | \
  aws s3 cp - s3://$BACKUP_S3_BUCKET/backups/$(date +%Y%m%d_%H%M%S).sql.gz

# Backup Redis
docker exec assetlens_redis_1 redis-cli SAVE
docker cp assetlens_redis_1:/data/dump.rdb - | \
  aws s3 cp - s3://$BACKUP_S3_BUCKET/redis/$(date +%Y%m%d_%H%M%S).rdb
```

## Troubleshooting

### Container Won't Start

**Check logs**:
```bash
docker-compose -f docker-compose.prod.yml logs backend
```

**Common issues**:
- Missing environment variables
- Database connection failure
- Port conflicts

**Solution**:
```bash
# Verify environment variables
docker-compose -f docker-compose.prod.yml config

# Check database connection
docker exec assetlens_backend_1 pg_isready -h postgres -U postgres
```

### Database Connection Failed

**Symptoms**: Backend shows "Connection refused" or "could not connect to server"

**Check**:
```bash
# Is postgres running?
docker-compose -f docker-compose.prod.yml ps postgres

# Check postgres logs
docker-compose -f docker-compose.prod.yml logs postgres

# Test connection
docker exec assetlens_postgres_1 psql -U postgres -c "SELECT 1"
```

**Solution**:
- Verify `DB_HOST=postgres` (not `localhost`)
- Check `DB_PASSWORD` matches in both services
- Ensure postgres is healthy before backend starts

### Frontend Can't Reach Backend

**Symptoms**: API calls fail with 502 or connection errors

**Check**:
```bash
# Test backend health from frontend container
docker exec assetlens_frontend_1 wget -O- http://backend:8000/health

# Test nginx proxy
docker exec assetlens_frontend_1 cat /etc/nginx/conf.d/default.conf
```

**Solution**:
- Verify `REACT_APP_API_URL=/api` in frontend build args
- Check nginx configuration is correct
- Ensure backend service name is `backend` in docker-compose

### High Memory Usage

**Check current usage**:
```bash
docker stats
```

**Optimization**:
```bash
# Reduce Redis memory limit
REDIS_MAXMEMORY=256mb

# Reduce database cache
# In docker-compose.prod.yml postgres command:
-c shared_buffers=128MB
-c effective_cache_size=512MB

# Reduce backend workers
# In Dockerfile.backend.prod CMD:
--workers 2
```

### Scraping Jobs Failing

**Check**:
```bash
# View scraper logs
docker exec assetlens_backend_1 cat /app/logs/scrapers.log

# Test Playwright installation
docker exec assetlens_backend_1 playwright --version
```

**Common issues**:
- Rate limiting by target sites
- Playwright browser not installed
- Network connectivity

### SSL Certificate Issues

Coolify handles SSL automatically. If issues occur:

1. Check domain DNS points to correct IP
2. Verify port 80/443 are open
3. Check Coolify SSL settings
4. Try forcing certificate renewal

## Updating

### Update Application Code

**Via Coolify** (recommended):
1. Push code changes to Git repository
2. In Coolify, click **"Redeploy"**
3. Coolify will rebuild images and restart services

**Manual update**:
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### Database Migrations

Migrations run automatically on backend startup via:
```bash
alembic upgrade head
```

To run manually:
```bash
docker exec assetlens_backend_1 alembic upgrade head
```

### Zero-Downtime Updates

For production environments:

1. Use blue-green deployment in Coolify
2. Run database migrations before deploying new backend
3. Keep API backward compatible during transition
4. Use health checks to verify new version before switching

## Performance Optimization

### CDN for Static Assets

Use Cloudflare or similar CDN:

1. Point domain through Cloudflare
2. Enable caching for static assets
3. Configure cache rules:
   - Cache `/static/*` for 1 year
   - Cache `/assets/*` for 1 year
   - Don't cache `/api/*`

### Database Optimization

```bash
# Enable connection pooling
DB_POOL_SIZE=20

# Optimize PostgreSQL
docker exec assetlens_postgres_1 psql -U postgres assetlens -c "VACUUM ANALYZE;"

# Create indexes (run after initial data import)
docker exec assetlens_backend_1 python /app/backend/etl/create_indexes.py
```

### Redis Caching

Configure aggressive caching:

```bash
# Increase cache TTL
CACHE_TTL=7200

# Cache more endpoints
# Modify backend to cache property listings, area stats, etc.
```

## Security Checklist

- [ ] Change default passwords
- [ ] Use strong `SECRET_KEY`
- [ ] Restrict `CORS_ORIGINS` to your domain
- [ ] Enable Coolify firewall
- [ ] Use HTTPS only (enforce in nginx)
- [ ] Regularly update Docker images
- [ ] Monitor security advisories
- [ ] Implement rate limiting (future)
- [ ] Enable database encryption (future)
- [ ] Set up automated backups
- [ ] Configure fail2ban (optional)

## Support

### Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/yourusername/AssetLens/issues)
- **Documentation**: Check `CLAUDE.md` for development details
- **Coolify Docs**: [docs.coolify.io](https://docs.coolify.io)

### Useful Commands

```bash
# View all containers
docker ps

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# View resource usage
docker stats

# Clean up old images
docker image prune -a

# Shell into backend
docker exec -it assetlens_backend_1 bash

# Shell into database
docker exec -it assetlens_postgres_1 psql -U postgres assetlens

# Export logs
docker-compose -f docker-compose.prod.yml logs > deployment.log
```

## Production Architecture

```
Internet
    ↓
[Coolify / Load Balancer]
    ↓
[Nginx Container:80/443]
  ├─ Serve React frontend
  └─ Proxy /api → Backend
        ↓
[Backend Container:8000]
  ├─ FastAPI application
  └─ Uvicorn (4 workers)
        ↓
    ┌───┴───┐
    ↓       ↓
[PostgreSQL] [Redis]
(Persistent volumes)
```

All internal networking, no exposed database ports.

---

**Production Checklist**

Before going live:

- [ ] Domain configured with SSL
- [ ] All environment variables set
- [ ] Database password changed
- [ ] Email alerts tested
- [ ] Scheduled jobs configured
- [ ] Backups automated
- [ ] Monitoring enabled
- [ ] Load tested with expected traffic
- [ ] Security review completed
- [ ] Documentation reviewed

**Your AssetLens instance should now be running in production!**

Visit: `https://assetlens.yourdomain.com`
