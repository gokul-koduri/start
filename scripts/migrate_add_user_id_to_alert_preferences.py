#!/usr/bin/env python3
"""Migration script: Add user_id column to alert_preferences table.

This migration adds user scoping to the alert_preferences table for per-user
alert notification settings.

Usage:
    python scripts/migrate_add_user_id_to_alert_preferences.py

Prerequisites:
    - MySQL server running with startup_research database
    - .env file configured with MySQL credentials
    - Existing alert_preferences table without user_id column

This script is idempotent - safe to run multiple times.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from db.connection import get_connection


def check_column_exists(cursor, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(
        """SELECT COUNT(*) as cnt
           FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME = %s
             AND COLUMN_NAME = %s""",
        (table, column),
    )
    return cursor.fetchone()["cnt"] > 0


def check_constraint_exists(cursor, constraint_name: str) -> bool:
    """Check if a constraint exists."""
    cursor.execute(
        """SELECT COUNT(*) as cnt
           FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
           WHERE TABLE_SCHEMA = DATABASE()
             AND CONSTRAINT_NAME = %s""",
        (constraint_name,),
    )
    return cursor.fetchone()["cnt"] > 0


def check_users_exist(cursor) -> list:
    """Get list of existing users for default assignment."""
    cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
    rows = cursor.fetchall()
    return [r["id"] for r in rows]


def migration_alert_preferences_user_id():
    """Migrate alert_preferences table to add user_id column."""
    conn = get_connection()
    cursor = conn.cursor()

    table_name = "alert_preferences"
    column_name = "user_id"
    default_user_id = 1

    print(f"\n{'='*60}")
    print(f"Migration: Add user_id to {table_name}")
    print(f"{'='*60}\n")

    # Step 1: Check if column already exists
    if check_column_exists(cursor, table_name, column_name):
        print(f"✓ Column '{column_name}' already exists in '{table_name}'")
        print("  Skipping column addition.")
    else:
        print(f"Step 1: Adding '{column_name}' column as nullable...")

        # Check for existing data that needs migration
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        existing_count = cursor.fetchone()["cnt"]

        if existing_count > 0:
            # Find or create a default user
            users = check_users_exist(cursor)
            if users:
                default_user_id = users[0]
                print(f"  Found existing users, will assign to user_id={default_user_id}")
            else:
                # Create a system user for migrated preferences
                print("  No users found, creating system user...")
                cursor.execute(
                    """INSERT INTO users (email, password_hash, display_name, role)
                       VALUES ('system@migrated', 'N/A', 'Migrated Preferences', 'admin')
                       ON DUPLICATE KEY UPDATE email=email"""
                )
                conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID() as id")
                default_user_id = cursor.fetchone()["id"]
                if default_user_id == 0:
                    cursor.execute("SELECT id FROM users WHERE email = 'system@migrated'")
                    default_user_id = cursor.fetchone()["id"]

        # Add nullable column first
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} INT NULL"
        )
        print(f"  ✓ Added nullable '{column_name}' column")

        # Step 2: Populate user_id for existing rows
        if existing_count > 0:
            print(f"Step 2: Assigning user_id={default_user_id} to {existing_count} existing rows...")
            cursor.execute(
                f"UPDATE {table_name} SET {column_name} = %s WHERE {column_name} IS NULL",
                (default_user_id,),
            )
            print(f"  ✓ Updated {cursor.rowcount} rows")

        # Step 3: Alter column to NOT NULL
        print("Step 3: Altering column to NOT NULL...")
        cursor.execute(
            f"ALTER TABLE {table_name} MODIFY {column_name} INT NOT NULL"
        )
        print("  ✓ Column is now NOT NULL")

    conn.commit()

    # Step 4: Add UNIQUE constraint
    unique_constraint = "uq_user_prefs"
    if not check_constraint_exists(cursor, unique_constraint):
        print(f"Step 4: Adding UNIQUE constraint '{unique_constraint}'...")
        cursor.execute(
            f"ALTER TABLE {table_name} ADD CONSTRAINT {unique_constraint} UNIQUE ({column_name})"
        )
        print(f"  ✓ Added UNIQUE constraint on '{column_name}'")
        conn.commit()
    else:
        print(f"  ✓ UNIQUE constraint '{unique_constraint}' already exists")

    # Step 5: Add foreign key (optional - may fail if circular reference issues)
    fk_constraint = "fk_alert_prefs_user"
    if not check_constraint_exists(cursor, fk_constraint):
        print(f"Step 5: Adding foreign key '{fk_constraint}'...")
        try:
            cursor.execute(
                f"""ALTER TABLE {table_name}
                    ADD CONSTRAINT {fk_constraint}
                    FOREIGN KEY ({column_name}) REFERENCES users(id) ON DELETE CASCADE"""
            )
            conn.commit()
            print("  ✓ Added foreign key constraint")
        except Exception as e:
            print(f"  ⚠ Could not add foreign key (may already exist): {e}")
            conn.rollback()
    else:
        print(f"  ✓ Foreign key '{fk_constraint}' already exists")

    # Verify the migration
    print("\nMigration verification:")
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['Field']}: {col['Type']} {'NOT NULL' if col['Null'] == 'NO' else 'NULL'}")

    cursor.close()
    conn.close()

    print(f"\n{'='*60}")
    print("Migration complete!")
    print(f"{'='*60}\n")

    return True


if __name__ == "__main__":
    try:
        migration_alert_preferences_user_id()
        print("Success!")
        sys.exit(0)
    except Exception as e:
        print(f"\nMigration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)