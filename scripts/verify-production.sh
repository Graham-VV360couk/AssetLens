#!/bin/bash
# AssetLens Production Verification Script
# Tests production Docker setup before deploying to Coolify

set -e

echo "======================================"
echo "AssetLens Production Verification"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker-compose.prod.yml exists
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}ERROR: docker-compose.prod.yml not found${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}WARNING: .env file not found${NC}"
    echo "Creating .env from .env.production template..."
    cp .env.production .env
    echo -e "${YELLOW}Please edit .env with your values before continuing${NC}"
    exit 1
fi

echo "Step 1: Checking required files..."
echo "-----------------------------------"

required_files=(
    "docker/Dockerfile.frontend.prod"
    "docker/Dockerfile.backend.prod"
    "nginx/frontend.conf"
    "nginx/nginx.conf"
    "backend/api/main.py"
    "frontend/src/services/api.js"
)

all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file (MISSING)"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = false ]; then
    echo -e "${RED}ERROR: Some required files are missing${NC}"
    exit 1
fi

echo ""
echo "Step 2: Validating docker-compose.prod.yml..."
echo "----------------------------------------------"
docker-compose -f docker-compose.prod.yml config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} docker-compose.prod.yml is valid"
else
    echo -e "${RED}✗${NC} docker-compose.prod.yml has errors"
    docker-compose -f docker-compose.prod.yml config
    exit 1
fi

echo ""
echo "Step 3: Checking environment variables..."
echo "------------------------------------------"

required_vars=(
    "DB_PASSWORD"
    "SECRET_KEY"
)

missing_vars=false
for var in "${required_vars[@]}"; do
    if grep -q "^${var}=<" .env || ! grep -q "^${var}=" .env; then
        echo -e "${RED}✗${NC} $var not set or using placeholder"
        missing_vars=true
    else
        echo -e "${GREEN}✓${NC} $var is configured"
    fi
done

if [ "$missing_vars" = true ]; then
    echo -e "${YELLOW}WARNING: Some required environment variables need configuration${NC}"
    echo "Edit .env before deployment"
fi

echo ""
echo "Step 4: Building production images..."
echo "--------------------------------------"
docker-compose -f docker-compose.prod.yml build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Production images built successfully"
else
    echo -e "${RED}✗${NC} Failed to build production images"
    exit 1
fi

echo ""
echo "Step 5: Checking image sizes..."
echo "--------------------------------"
echo "Frontend image:"
docker images | grep assetlens.*frontend | head -1
echo "Backend image:"
docker images | grep assetlens.*backend | head -1

echo ""
echo "Step 6: Starting production services..."
echo "----------------------------------------"
docker-compose -f docker-compose.prod.yml up -d
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Services started"
else
    echo -e "${RED}✗${NC} Failed to start services"
    exit 1
fi

echo ""
echo "Step 7: Waiting for services to be healthy..."
echo "----------------------------------------------"
sleep 10

# Check service health
services=("postgres" "redis" "backend" "frontend")
for service in "${services[@]}"; do
    status=$(docker-compose -f docker-compose.prod.yml ps -q $service | xargs docker inspect -f '{{.State.Health.Status}}' 2>/dev/null || echo "running")
    if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
        echo -e "${GREEN}✓${NC} $service is $status"
    else
        echo -e "${RED}✗${NC} $service is $status"
    fi
done

echo ""
echo "Step 8: Testing endpoints..."
echo "-----------------------------"

# Wait a bit more for services to fully start
sleep 5

# Test health endpoint
echo -n "Testing /health... "
health_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)
if [ "$health_response" = "200" ]; then
    echo -e "${GREEN}✓${NC} (HTTP $health_response)"
    curl -s http://localhost/health | jq '.' 2>/dev/null || curl -s http://localhost/health
else
    echo -e "${RED}✗${NC} (HTTP $health_response)"
fi

echo ""
echo -n "Testing /api/status... "
status_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/status)
if [ "$status_response" = "200" ]; then
    echo -e "${GREEN}✓${NC} (HTTP $status_response)"
else
    echo -e "${RED}✗${NC} (HTTP $status_response)"
fi

echo ""
echo -n "Testing / (frontend)... "
frontend_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
if [ "$frontend_response" = "200" ] || [ "$frontend_response" = "304" ]; then
    echo -e "${GREEN}✓${NC} (HTTP $frontend_response)"
else
    echo -e "${RED}✗${NC} (HTTP $frontend_response)"
fi

echo ""
echo -n "Testing /docs (API documentation)... "
docs_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/docs)
if [ "$docs_response" = "200" ]; then
    echo -e "${GREEN}✓${NC} (HTTP $docs_response)"
else
    echo -e "${RED}✗${NC} (HTTP $docs_response)"
fi

echo ""
echo "Step 9: Checking logs for errors..."
echo "------------------------------------"
echo "Backend logs:"
docker-compose -f docker-compose.prod.yml logs --tail 10 backend

echo ""
echo "======================================"
echo "Verification Complete!"
echo "======================================"
echo ""
echo "Services are running. You can:"
echo "  - View frontend: http://localhost"
echo "  - View API docs: http://localhost/docs"
echo "  - Check health: http://localhost/health"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose -f docker-compose.prod.yml down"
echo ""
echo -e "${GREEN}Ready for Coolify deployment!${NC}"
