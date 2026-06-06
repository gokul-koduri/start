#!/bin/bash
# Restore database from backup
# Usage: ./scripts/restore_db.sh <backup_file.sql.gz>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -la data/backups/*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-startup2024}"
DB_NAME="${MYSQL_DATABASE:-startup_research}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ File not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will REPLACE the current database!"
echo "   Database: $DB_NAME"
echo "   Backup:   $BACKUP_FILE"
read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then echo "Aborted."; exit 0; fi

echo "Creating safety backup first..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/backup_db.sh"

echo "Restoring from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | mysql \
    -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" 2>/dev/null

echo "✅ Restored. Verifying..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
    SELECT 'failed_startups' as tbl, COUNT(*) as cnt FROM failed_startups
    UNION ALL SELECT 'raw_signals', COUNT(*) FROM raw_signals
    UNION ALL SELECT 'opportunity_scores', COUNT(*) FROM opportunity_scores
" 2>/dev/null
echo "✅ Verified."
