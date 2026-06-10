#!/usr/bin/env bash
# fly-start.sh — Starts MySQL, seeds data, launches API
# Runs inside the Fly.io container on every boot.
set -euo pipefail

MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-/data/mysql}"
MYSQL_RUN_DIR="/var/run/mysqld"
DB_NAME="${MYSQL_DATABASE:-startup_research}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-}"

echo "=== Fly.io Startup ==="

# ── 1. Set up MySQL data directory on persistent volume ──
if [ ! -d "${MYSQL_DATA_DIR}" ]; then
    echo "[1/6] Initializing MySQL data directory..."
    mkdir -p "${MYSQL_DATA_DIR}"
    # Install default MySQL tables into our volume
    mysqld --initialize-insecure --user=root --datadir="${MYSQL_DATA_DIR}" 2>/dev/null || true
else
    echo "[1/6] MySQL data directory exists (persisted from previous deploy)"
fi

mkdir -p "${MYSQL_RUN_DIR}"
chown root:root "${MYSQL_RUN_DIR}"

# ── 2. Start MySQL ──
echo "[2/6] Starting MySQL..."
mysqld --user=root --datadir="${MYSQL_DATA_DIR}" --skip-bind-address &
MYSQL_PID=$!

# Wait for MySQL to be ready
echo "  Waiting for MySQL to accept connections..."
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if mysqladmin ping --silent 2>/dev/null; then
        echo "  MySQL: ready"
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "  ERROR: MySQL failed to start within ${MAX_WAIT}s"
    exit 1
fi

# ── 3. Create database and user if needed ──
echo "[3/6] Ensuring database exists..."
mysql -u root -e "CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null

if [ -n "${DB_PASS}" ]; then
    mysql -u root -e "ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';" 2>/dev/null || \
    mysql -u root -e "CREATE USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';" 2>/dev/null || true
    mysql -u root -e "GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';" 2>/dev/null || true
    mysql -u root -e "FLUSH PRIVILEGES;" 2>/dev/null
fi

# ── 4. Seed data if database is empty ──
ROW_COUNT=$(mysql -u "${DB_USER}" ${DB_PASS:+-p"${DB_PASS}"} -N -e "SELECT COUNT(*) FROM \`${DB_NAME}\`.failed_startups;" 2>/dev/null || echo "0")

if [ "${ROW_COUNT}" = "0" ] || [ -z "${ROW_COUNT}" ]; then
    echo "[4/6] Seeding database (first boot)..."
    python3 seed_data.py 2>&1 | tail -5
    echo "  Seed complete"
else
    echo "[4/6] Database already seeded (${ROW_COUNT} startups)"
fi

# ── 5. Start API server ──
echo "[5/6] Starting API server on port 8000..."
cd /app

# ── 6. Health check info ──
echo "[6/6] Ready!"
echo "  API:      http://localhost:8000"
echo "  Dashboard: http://localhost:8000/"
echo "  Health:   http://localhost:8000/api/health"
echo "  Docs:     http://localhost:8000/docs"

# Start the API (this process becomes PID 1 for the container)
exec python3 api_server.py --host 0.0.0.0 --port 8000
