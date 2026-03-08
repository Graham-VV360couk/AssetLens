#!/bin/bash
# ============================================================
# AssetLens Frontend Build Script
# Builds React app ready for upload to assetlens.geeky.net
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DEPLOY_DIR="$PROJECT_DIR/deploy"

echo "============================================================"
echo "  AssetLens Frontend Build"
echo "  Target: assetlens.geeky.net"
echo "============================================================"

# Prompt for API URL if not set
if [ -z "${REACT_APP_API_URL:-}" ]; then
    read -p "Enter your backend API URL (e.g. https://assetlens-api.onrender.com): " REACT_APP_API_URL
    export REACT_APP_API_URL
fi

echo ""
echo "API URL: $REACT_APP_API_URL"
echo ""

# Install dependencies if needed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Installing npm dependencies..."
    cd "$FRONTEND_DIR" && npm ci
fi

# Build
echo "Building React app..."
cd "$FRONTEND_DIR"
REACT_APP_API_URL="$REACT_APP_API_URL" npm run build

# Create deploy package
echo "Packaging for upload..."
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"
cp -r "$FRONTEND_DIR/build/." "$DEPLOY_DIR/"

# Create zip for FTP upload
if command -v zip &>/dev/null; then
    cd "$DEPLOY_DIR"
    zip -r "$PROJECT_DIR/assetlens-frontend.zip" .
    echo ""
    echo "============================================================"
    echo "  Build complete!"
    echo ""
    echo "  Files ready in:  deploy/"
    echo "  ZIP archive:     assetlens-frontend.zip"
    echo ""
    echo "  Upload steps:"
    echo "  1. Log in to geeky.net cPanel"
    echo "  2. Create subdomain: assetlens.geeky.net"
    echo "     pointing to public_html/assetlens/"
    echo "  3. Upload contents of deploy/ (or extract ZIP)"
    echo "     into public_html/assetlens/"
    echo "  4. Verify .htaccess uploaded (enable hidden files in FTP)"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "  Build complete!"
    echo "  Upload the contents of deploy/ to public_html/assetlens/"
    echo "  on geeky.net via FTP/cPanel File Manager"
    echo "  IMPORTANT: ensure .htaccess is uploaded (it may be hidden)"
    echo "============================================================"
fi
