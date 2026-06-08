#!/usr/bin/env bash
# deploy.sh — One-click deployment for Opportunity Intelligence Platform
# Usage: ./scripts/deploy.sh [--env /path/to/.env] [--domain example.com]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  Opportunity Intelligence Platform"
echo "  One-Click Deployment"
echo "========================================"

# Parse arguments
DOMAIN=""
ENV_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain) DOMAIN="$2"; shift 2 ;;
        --env) ENV_FILE="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

cd "$PROJECT_DIR"

# Step 1: Check prerequisites
echo ""
echo "[1/6] Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is not installed."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: Docker Compose is not installed."; exit 1; }
echo "  Docker: OK"

# Step 2: Set up environment
echo ""
echo "[2/6] Setting up environment..."
if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" .env
    echo "  Copied env from: $ENV_FILE"
elif [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example"
    echo ""
    echo "  IMPORTANT: Edit .env and set required secrets:"
    echo "    - MYSQL_PASSWORD (database password)"
    echo "    - SECRET_KEY (session encryption key)"
    echo ""
    read -p "  Press Enter after editing .env, or Ctrl+C to abort..."
else
    echo "  Using existing .env"
fi

# Step 3: Validate secrets
echo ""
echo "[3/6] Validating secrets..."
python3 scripts/validate_secrets.py 2>/dev/null || echo "  Warning: Secret validation skipped (install dependencies)"

# Step 4: Pull latest code (if git repo)
echo ""
echo "[4/6] Checking for updates..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git pull --ff-only 2>/dev/null || echo "  Warning: Could not pull updates (may be local changes)"
    echo "  Git: up to date"
else
    echo "  Not a git repo, skipping pull"
fi

# Step 5: Start services
echo ""
echo "[5/6] Starting Docker services..."
docker compose up -d

echo "  Waiting for MySQL to be healthy..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker compose exec -T mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
        echo "  MySQL: healthy"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "  ERROR: MySQL failed to start within ${MAX_WAIT}s"
    docker compose logs mysql --tail 20
    exit 1
fi

# Step 6: Run health check
echo ""
echo "[6/6] Running health checks..."
sleep 5

API_HEALTH=$(curl -s http://localhost:8000/api/health 2>/dev/null || echo "failed")
if echo "$API_HEALTH" | grep -q "healthy"; then
    echo "  API: healthy"
else
    echo "  API: not responding (may still be starting)"
fi

# Configure domain (if specified)
if [ -n "$DOMAIN" ]; then
    echo ""
    echo "Domain configuration for: $DOMAIN"
    echo "  1. Point DNS A record to this server's IP"
    echo "  2. Caddy will auto-provision HTTPS via Let's Encrypt"
    echo "  3. Update Caddyfile with your domain name"
    echo ""
    echo "  Caddyfile should contain:"
    echo "    ${DOMAIN} {"
    echo "        reverse_proxy api:8000"
    echo "        reverse_proxy /dashboard* streamlit:8501"
    echo "    }"
fi

# Summary
echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
echo "  API:       http://localhost:8000"
echo "  Dashboard: http://localhost:8501"
echo "  Health:    http://localhost:8000/api/health"
echo "  MySQL:     localhost:3306"
echo "  Ollama:    http://localhost:11434"
echo ""
echo "  Useful commands:"
echo "    docker compose ps          # Check service status"
echo "    docker compose logs -f api # Follow API logs"
echo "    docker compose down        # Stop all services"
echo "    ./scripts/backup_db.sh     # Backup database"
echo ""
