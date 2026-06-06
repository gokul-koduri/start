#!/bin/bash
# MySQL Backup Script — RUN DAILY via cron
# Cron: 0 2 * * * /path/to/scripts/backup_db.sh >> /path/to/data/logs/backup.log 2>&1

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-startup2024}"
DB_NAME="${MYSQL_DATABASE:-startup_research}"
BACKUP_DIR="${PROJECT_DIR}/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql.gz"
RETENTION_DAYS=30
S3_BUCKET="${S3_BACKUP_BUCKET:-}"

mkdir -p "$BACKUP_DIR" "$PROJECT_DIR/data/logs"

echo "[$(date)] Starting backup of ${DB_NAME}..."

mysqldump \
    -h "$DB_HOST" \
    -P "$DB_PORT" \
    -u "$DB_USER" \
    -p"$DB_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    --add-drop-table \
    --quick \
    "$DB_NAME" 2>/dev/null | gzip > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] ✅ Backup created: $BACKUP_FILE ($SIZE)"
else
    echo "[$(date)] ❌ Backup FAILED!"
    exit 1
fi

if [ -n "$S3_BUCKET" ]; then
    echo "[$(date)] Uploading to S3..."
    aws s3 cp "$BACKUP_FILE" "$S3_BUCKET/$(basename $BACKUP_FILE)" \
        --storage-class STANDARD_IA 2>&1 && echo "[$(date)] ✅ S3 done" \
        || echo "[$(date)] ⚠️ S3 failed (local backup OK)"
fi

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null
echo "[$(date)] Backup complete. Cleaned backups older than $RETENTION_DAYS days."
