"""Flexible date parsing utilities."""

import re
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

# Month name mapping
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_fuzzy_year(text: str | None) -> int | None:
    """Extract a year from fuzzy text like 'Dec 2024', '2023-24', 'Q1 2025'.

    Returns the most relevant year as an integer, or None if not parseable.
    """
    if not text:
        return None

    text = text.strip()

    # "YYYY" (4 digits starting with 19 or 20)
    match = re.search(r"\b((?:19|20)\d{2})\b", text)
    if match:
        year = int(match.group(1))
        if 1990 <= year <= 2030:
            return year

    return None


def parse_iso_date(text: str | None) -> str | None:
    """Normalize various date formats to ISO 8601 (YYYY-MM-DD).

    Handles: ISO dates, RFC 2822, "Dec 2024", "Q1 2025", etc.
    Returns ISO string or None if unparseable.
    """
    if not text:
        return None

    text = text.strip()

    # Already ISO format
    if re.match(r"\d{4}-\d{2}-\d{2}", text):
        return text[:10]

    # RFC 2822 / common date format
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%B %d, %Y", "%B %Y", "%b %Y", "%d %b %Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    _logger.debug("Could not parse date: '%s'", text)
    return None


def parse_quarter(period: str) -> int | None:
    """Parse BLS-style period string like 'Q01', 'Q02' to quarter number."""
    match = re.match(r"Q(\d)", period.upper().strip())
    if match:
        q = int(match.group(1))
        return q if 1 <= q <= 4 else None
    return None
