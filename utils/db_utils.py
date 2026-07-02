"""Batch database write utilities for efficient bulk operations.

Usage:
    from utils.db_utils import bulk_upsert, bulk_insert

    rows = [
        {"entity_name": "OpenAI", "composite_score": 90.0, "trend": "rising"},
        {"entity_name": "Anthropic", "composite_score": 85.0, "trend": "stable"},
    ]

    bulk_upsert(conn, "opportunity_scores", rows,
                key_columns=["entity_name"], batch_size=100)

    bulk_insert(conn, "score_deltas", rows, batch_size=50)
"""

import logging
from typing import Any

_logger = logging.getLogger(__name__)


def bulk_insert(
    conn: Any,
    table: str,
    rows: list[dict],
    batch_size: int = 100,
) -> int:
    """Insert rows in batches using executemany.

    Args:
        conn: Database connection with cursor() method.
        table: Target table name.
        rows: List of dicts with column:value pairs.
        batch_size: Rows per INSERT statement.

    Returns:
        Total rows inserted.
    """
    if not rows:
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    columns_str = ", ".join(f"`{c}`" for c in columns)
    sql = f"INSERT INTO `{table}` ({columns_str}) VALUES ({placeholders})"

    total = 0
    cursor = conn.cursor()

    try:
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            values = [tuple(row[c] for c in columns) for row in batch]
            cursor.executemany(sql, values)
            total += len(batch)

        conn.commit()
        _logger.info(
            "bulk_insert: %d rows into %s (%d batches)",
            total,
            table,
            (len(rows) + batch_size - 1) // batch_size,
        )
    except Exception as e:
        conn.rollback()
        _logger.error("bulk_insert failed for %s: %s", table, e)
        raise
    finally:
        cursor.close()

    return total


def bulk_upsert(
    conn: Any,
    table: str,
    rows: list[dict],
    key_columns: list[str] | None = None,
    batch_size: int = 100,
) -> int:
    """Insert or update rows in batches using INSERT ... ON DUPLICATE KEY UPDATE.

    Args:
        conn: Database connection with cursor() method.
        table: Target table name.
        rows: List of dicts with column:value pairs.
        key_columns: Columns used for deduplication. If None, uses all columns
                     for ON DUPLICATE KEY UPDATE (MySQL requires unique key).
        batch_size: Rows per statement.

    Returns:
        Total rows processed.
    """
    if not rows:
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    columns_str = ", ".join(f"`{c}`" for c in columns)

    # Build ON DUPLICATE KEY UPDATE clause for non-key columns
    update_cols = [c for c in columns if key_columns is None or c not in key_columns]
    update_clause = ", ".join(f"`{c}` = VALUES(`{c}`)" for c in update_cols)

    sql = (
        f"INSERT INTO `{table}` ({columns_str}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_clause}"
    )

    total = 0
    cursor = conn.cursor()

    try:
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            values = [tuple(row[c] for c in columns) for row in batch]
            cursor.executemany(sql, values)
            total += len(batch)

        conn.commit()
        _logger.info(
            "bulk_upsert: %d rows into %s (%d batches)",
            total,
            table,
            (len(rows) + batch_size - 1) // batch_size,
        )
    except Exception as e:
        conn.rollback()
        _logger.error("bulk_upsert failed for %s: %s", table, e)
        raise
    finally:
        cursor.close()

    return total
