#!/usr/bin/env python3
"""One-time migration script: SQLite -> MySQL.

Usage:
    python scripts/migrate_sqlite_to_mysql.py

Prerequisites:
    - MySQL server running with startup_research database created
    - .env file configured with MySQL credentials
    - Existing data/startup_research.db SQLite file

To create the MySQL database first:
    mysql -u root -e "CREATE DATABASE IF NOT EXISTS startup_research
                      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from db.connection import get_connection  # noqa: E402
from db import schema  # noqa: E402

SQLITE_DB_PATH = Path(__file__).parent.parent / "data" / "startup_research.db"

# Generated columns that MySQL computes automatically — must be excluded from INSERT
GENERATED_COLUMNS = {
    "bls_survival_rates": {"quarter_key"},
}

# Column name mappings: SQLite name -> MySQL name (for reserved words etc.)
COLUMN_ALIASES = {
    "agent_runs": {"trigger": "trigger_type"},
}

# Migration order — no FK constraints, ordered by approximate size
TABLES_IN_ORDER = [
    "failure_reasons_taxonomy",
    "failure_idea_patterns",
    "manufacturing_failure_categories",
    "revival_industries",
    "geographic_hotspots",
    "failed_startups",
    "bls_survival_rates",
    "reshoring_data",
    "reshoring_summary_stats",
    "news_articles",
    "discovered_sources",
    "collection_runs",
    "agent_runs",
    "analysis_failure_patterns",
    "analysis_survival_trends",
    "analysis_revival_opportunities",
    "analysis_geographic_strategy",
    "analysis_news_intelligence",
    "analysis_opportunity_pipeline",
    "analysis_whale_investors",
]


def migrate():
    if not SQLITE_DB_PATH.exists():
        print(f"SQLite database not found at {SQLITE_DB_PATH}")
        sys.exit(1)

    # Connect to SQLite (read data)
    sqlite_conn = sqlite3.connect(str(SQLITE_DB_PATH))
    sqlite_conn.row_factory = sqlite3.Row

    # Connect to MySQL (write data)
    mysql_conn = get_connection()

    # Initialize MySQL schema
    schema.init_schema(mysql_conn)

    total_migrated = 0

    for table_name in TABLES_IN_ORDER:
        # Check if table exists in SQLite
        try:
            sqlite_cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
            sqlite_rows = sqlite_cursor.fetchall()
        except Exception:
            print(f"  {table_name}: does not exist in SQLite (skipped)")
            continue

        if not sqlite_rows:
            print(f"  {table_name}: 0 rows (skipped)")
            continue

        # Get all column names from first row
        all_columns = list(sqlite_rows[0].keys())

        # Exclude generated columns for this table
        generated = GENERATED_COLUMNS.get(table_name, set())
        aliases = COLUMN_ALIASES.get(table_name, {})
        columns = [c for c in all_columns if c not in generated and c != "id"]

        # Map column names (e.g., trigger -> trigger_type)
        mysql_columns = [aliases.get(c, c) for c in columns]

        col_list = ", ".join(f"`{c}`" for c in mysql_columns)
        placeholders = ", ".join(["%s"] * len(columns))

        # Insert into MySQL — use REPLACE to handle any existing data
        sql = f"REPLACE INTO `{table_name}` ({col_list}) VALUES ({placeholders})"

        mysql_cursor = mysql_conn.cursor()
        inserted = 0

        # Insert rows one at a time to handle errors gracefully
        for row in sqlite_rows:
            values = tuple(row[col] for col in columns)
            try:
                mysql_cursor.execute(sql, values)
                inserted += 1
            except Exception as e:
                print(f"    WARNING: row skipped in {table_name}: {e}")
                continue

        mysql_conn.commit()
        total_migrated += inserted
        print(
            f"  {table_name}: {len(sqlite_rows)} SQLite rows -> {inserted} MySQL rows inserted"
        )
        mysql_cursor.close()

    sqlite_conn.close()
    mysql_conn.close()

    print(f"\nMigration complete: {total_migrated} total rows migrated")


if __name__ == "__main__":
    migrate()
