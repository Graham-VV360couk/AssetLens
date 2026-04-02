"""AssetLens FastAPI Application."""
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routers import properties, areas, dashboard, scrapers, scoring, ai_analysis, profile, ads, scan, auth, billing, account, listings, auction_listings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AssetLens API starting up...")
    yield
    logger.info("AssetLens API shutting down...")


app = FastAPI(
    title="AssetLens API",
    description="UK Property Investment Intelligence Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router)
app.include_router(areas.router)
app.include_router(dashboard.router)
app.include_router(scrapers.router)
app.include_router(scoring.router)
app.include_router(ai_analysis.router)
app.include_router(profile.router)
app.include_router(ads.router)
app.include_router(scan.router)
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(account.router)
app.include_router(listings.router)
app.include_router(auction_listings.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "assetlens-api"}


@app.get("/api/status")
def api_status():
    return {
        "status": "ok",
        "version": app.version,
        "uptime_seconds": round(time.time() - _start_time, 1),
    }


@app.get("/")
def root():
    return {"message": "AssetLens API", "docs": "/docs"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
