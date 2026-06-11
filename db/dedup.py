"""Deduplication utilities for the Startup Research database."""

import logging

_logger = logging.getLogger(__name__)


def dedup_startup(conn, name: str, region: str) -> bool:
    """Check if a (name, region) pair already exists in failed_startups.

    Returns True if the record exists (should be skipped).
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM failed_startups WHERE name = %s AND region = %s",
        (name, region),
    )
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def dedup_news_article(conn, url: str) -> bool:
    """Check if a news article URL already exists.

    Returns True if the record exists.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM news_articles WHERE url = %s", (url,))
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def dedup_bls_rate(
    conn, naics_code: str, year: int, quarter: int | None = None
) -> bool:
    """Check if a BLS rate record already exists.

    Returns True if the record exists.
    """
    cursor = conn.cursor()
    if quarter is not None:
        cursor.execute(
            "SELECT 1 FROM bls_survival_rates WHERE naics_code = %s AND year = %s AND quarter = %s",
            (naics_code, year, quarter),
        )
    else:
        cursor.execute(
            "SELECT 1 FROM bls_survival_rates WHERE naics_code = %s AND year = %s AND quarter IS NULL",
            (naics_code, year),
        )
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def dedup_reshoring(conn, data_year: int, industry: str | None) -> bool:
    """Check if a reshoring data record already exists.

    Returns True if the record exists.
    """
    cursor = conn.cursor()
    if industry:
        cursor.execute(
            "SELECT 1 FROM reshoring_data WHERE data_year = %s AND industry = %s",
            (data_year, industry),
        )
    else:
        cursor.execute(
            "SELECT 1 FROM reshoring_data WHERE data_year = %s AND industry IS NULL",
            (data_year,),
        )
    row = cursor.fetchone()
    cursor.close()
    return row is not None
