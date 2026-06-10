#!/usr/bin/env bash
# railway-start.sh — Starts API with managed MySQL on Railway
# Railway auto-injects: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
set -euo pipefail

DB_HOST="${MYSQL_HOST:-localhost}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-}"
DB_NAME="${MYSQL_DATABASE:-startup_research}"

echo "=== Railway Startup ==="
echo "  MySQL: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# ── 1. Wait for MySQL to be ready ──
echo "[1/3] Waiting for MySQL..."
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if python3 -c "
import pymysql, sys
try:
    pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'),
                    user='${DB_USER}', password='${DB_PASS}',
                    connect_timeout=3)
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; then
        echo "  MySQL: ready"
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "  WARN: MySQL not ready after ${MAX_WAIT}s, proceeding anyway"
fi

# ── 1b. Create database if it doesn't exist ──
echo "[1b/3] Creating database ${DB_NAME} if needed..."
python3 -c "
import pymysql, sys
try:
    conn = pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'),
                           user='${DB_USER}', password='${DB_PASS}',
                           connect_timeout=10)
    cur = conn.cursor()
    cur.execute('CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    conn.commit()
    conn.close()
    print('  Database ready')
except Exception as e:
    print(f'  WARN: Could not create database: {e}')
    sys.exit(0)
" 2>&1

# ── 2. Seed data if database is empty ──
ROW_COUNT=$(python3 -c "
import pymysql
try:
    conn = pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'),
                           user='${DB_USER}', password='${DB_PASS}',
                           database='${DB_NAME}', connect_timeout=5)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM failed_startups')
    print(cur.fetchone()[0])
    conn.close()
except:
    print('0')
" 2>/dev/null || echo "0")

if [ "${ROW_COUNT}" = "0" ] || [ -z "${ROW_COUNT}" ]; then
    echo "[2/3] Seeding database (first boot)..."
    python3 seed_data.py 2>&1 | tail -5
    echo "  Seed complete"
else
    echo "[2/3] Database already seeded (${ROW_COUNT} startups)"
fi

# ── 3. Start API server ──
echo "[3/3] Starting API server on port ${PORT:-8000}..."
echo "  Dashboard: http://0.0.0.0:${PORT:-8000}/"
echo "  Health:    http://0.0.0.0:${PORT:-8000}/api/health"

exec python3 api_server.py --host 0.0.0.0 --port "${PORT:-8000}"
