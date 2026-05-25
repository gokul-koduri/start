"""Deduplication utilities for the Startup Research database."""

import sqlite3
import logging

_logger = logging.getLogger(__name__)


def dedup_startup(conn: sqlite3.Connection, name: str, region: str) -> bool:
    """Check if a (name, region) pair already exists in failed_startups.

    Returns True if the record exists (should be skipped).
    """
    row = conn.execute(
        "SELECT 1 FROM failed_startups WHERE name = ? AND region = ?",
        (name, region),
    ).fetchone()
    return row is not None


def dedup_news_article(conn: sqlite3.Connection, url: str) -> bool:
    """Check if a news article URL already exists.

    Returns True if the record exists.
    """
    row = conn.execute(
        "SELECT 1 FROM news_articles WHERE url = ?", (url,)
    ).fetchone()
    return row is not None


def dedup_bls_rate(conn: sqlite3.Connection, naics_code: str, year: int, quarter: int) -> bool:
    """Check if a BLS rate record already exists.

    Returns True if the record exists.
    """
    row = conn.execute(
        "SELECT 1 FROM bls_survival_rates WHERE naics_code = ? AND year = ? AND quarter = ?",
        (naics_code, year, quarter),
    ).fetchone()
    return row is not None


def dedup_reshoring(conn: sqlite3.Connection, data_year: int, industry: str | None) -> bool:
    """Check if a reshoring data record already exists.

    Returns True if the record exists.
    """
    if industry:
        row = conn.execute(
            "SELECT 1 FROM reshoring_data WHERE data_year = ? AND industry = ?",
            (data_year, industry),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM reshoring_data WHERE data_year = ? AND industry IS NULL",
            (data_year,),
        ).fetchone()
    return row is not None
