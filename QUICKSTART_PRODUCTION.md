# AssetLens Production - Quick Start

## 🚀 Fast Track to Production

### Step 1: Configure Environment (2 minutes)

```bash
# Copy template
cp .env.production .env

# Edit with your values
nano .env
```

**Required values**:
```bash
DB_PASSWORD=<generate-secure-password>
SECRET_KEY=<openssl-rand-hex-32>
CORS_ORIGINS=https://assetlens.yourdomain.com
```

**Generate secrets**:
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate DB_PASSWORD
openssl rand -base64 32
```

### Step 2: Test Locally (5 minutes)

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to start (30 seconds)
sleep 30

# Test health
curl http://localhost/health
# Expected: {"status":"healthy","service":"assetlens-api",...}

# Test frontend
curl http://localhost/
# Expected: HTML response

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop when done
docker-compose -f docker-compose.prod.yml down
```

**Or use verification script**:
```bash
bash scripts/verify-production.sh
```

### Step 3: Deploy to Coolify (5 minutes)

1. **Create Service**
   - Coolify → New Resource → Docker Compose
   - Name: `assetlens`
   - Upload `docker-compose.prod.yml`

2. **Add Environment Variables**
   - Copy all variables from `.env`
   - Paste into Coolify environment section

3. **Configure Domain**
   - Domain: `assetlens.yourdomain.com`
   - Enable SSL (Let's Encrypt)

4. **Deploy**
   - Click "Deploy"
   - Wait 2-5 minutes
   - Check logs for errors

5. **Verify**
   ```bash
   curl https://assetlens.yourdomain.com/health
   ```

### Step 4: Configure Cron Jobs (5 minutes)

In Coolify scheduled tasks:

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

## ✅ Deployment Checklist

- [ ] `.env` configured with real values
- [ ] `DB_PASSWORD` changed to secure value
- [ ] `SECRET_KEY` generated
- [ ] `CORS_ORIGINS` set to your domain
- [ ] Local test passed
- [ ] Coolify service created
- [ ] Domain configured with SSL
- [ ] Deployment successful
- [ ] Health check passing
- [ ] Frontend accessible
- [ ] API docs accessible
- [ ] Cron jobs configured
- [ ] Backups scheduled

## 🔍 Key Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Health check | `{"status":"healthy"}` |
| `/api/status` | API status | `{"status":"operational"}` |
| `/` | Frontend | React app HTML |
| `/docs` | API documentation | Swagger UI |

## 📁 Key Files

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production orchestration |
| `.env.production` | Environment template |
| `docker/Dockerfile.*.prod` | Production images |
| `nginx/*.conf` | Nginx configuration |
| `DEPLOYMENT.md` | Full deployment guide |

## 🛠️ Common Commands

```bash
# Build production
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down

# Check health
curl http://localhost/health

# Backup database
docker exec assetlens_postgres_1 pg_dump -U postgres assetlens > backup.sql

# Access backend shell
docker exec -it assetlens_backend_1 bash

# Access database
docker exec -it assetlens_postgres_1 psql -U postgres assetlens
```

## 🔒 Security Quick Check

- [ ] Changed default `DB_PASSWORD`
- [ ] Generated unique `SECRET_KEY`
- [ ] Set `CORS_ORIGINS` to specific domain (not `*`)
- [ ] Configured HTTPS/SSL
- [ ] Database not exposed to internet
- [ ] Firewall configured

## 🐛 Quick Troubleshooting

**Backend won't start**
```bash
docker logs assetlens_backend_1
# Check: Missing env vars, DB connection
```

**Database connection failed**
```bash
docker exec assetlens_backend_1 pg_isready -h postgres -U postgres
# Ensure DB_HOST=postgres (not localhost)
```

**Frontend can't reach API**
```bash
docker exec assetlens_frontend_1 wget -O- http://backend:8000/health
# Verify REACT_APP_API_URL=/api
```

## 📚 Full Documentation

- **Comprehensive Guide**: [DEPLOYMENT.md](DEPLOYMENT.md) (detailed deployment steps)
- **Quick Reference**: [README.production.md](README.production.md) (command reference)
- **Summary**: [PRODUCTION_SETUP_SUMMARY.md](PRODUCTION_SETUP_SUMMARY.md) (implementation details)
- **Project Info**: [CLAUDE.md](CLAUDE.md) (development guidelines)

## 🎯 Success Criteria

Your deployment is successful when:

✅ Health check returns `{"status":"healthy"}`
✅ Frontend loads at `https://yourdomain.com`
✅ API docs accessible at `https://yourdomain.com/docs`
✅ No errors in logs
✅ All services running and healthy

## 💡 Pro Tips

1. **Test locally first** - Always run `docker-compose -f docker-compose.prod.yml up` locally before deploying
2. **Use verification script** - Run `bash scripts/verify-production.sh` for comprehensive testing
3. **Check logs early** - Monitor deployment logs in Coolify to catch issues fast
4. **Backup immediately** - Set up automated backups right after first deployment
5. **Start with sample data** - Test with small dataset before full data import

## ⚡ Quick Architecture

```
Internet → Coolify (SSL) → Nginx (80/443) → Backend (8000)
                                            ↓
                                        PostgreSQL + Redis
                                        (Internal only)
```

## 🚨 Need Help?

1. Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
2. Run verification script: `bash scripts/verify-production.sh`
3. Check logs: `docker-compose -f docker-compose.prod.yml logs -f`
4. Review health: `curl http://localhost/health`

## 📞 Support

- **Issues**: GitHub Issues
- **Docs**: See `DEPLOYMENT.md`
- **Development**: See `CLAUDE.md`

---

**Total deployment time: ~15-20 minutes**

**Your AssetLens instance will be live at**: `https://assetlens.yourdomain.com` 🎉
