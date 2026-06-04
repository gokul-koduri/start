"""Funding events collector — monitors startup funding rounds and deals.

Funding events are the strongest signal in the scoring engine (weight: 25).
This collector monitors:
  - Crunchbase-related RSS feeds
  - AngelList/Wellfound
  - TechCrunch funding news
  - SEC Form D filings (required for private company fundraising)

Note: Full Crunchbase API requires a paid license. This collector uses
publicly available RSS feeds and search APIs as alternatives.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

import feedparser

from collectors.base import BaseCollector, CollectionResult
from db.dedup import dedup_news_article
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

# Funding amount extraction patterns
_AMOUNT_PATTERN = re.compile(
    r"\$([\d.,]+)\s*(million|M|billion|B|K|thousand)?",
    re.IGNORECASE,
)

_ROUND_TYPE_PATTERN = re.compile(
    r"\b(Series [A-Z]|Seed|Pre-?Seed|Series \d+|Angel|Venture|Growth|"
    r"IPO|Secondary|Convertible|SAFE|Grant|Debt)\b",
    re.IGNORECASE,
)


class FundingEventsCollector(BaseCollector):
    """Collects funding event signals from public news and filing sources."""

    @property
    def name(self) -> str:
        return "funding_events"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        funding_config = self.config.get("funding", {})
        sources = funding_config.get("sources", [])

        if not sources:
            # Default: TechCrunch funding category RSS + Google News funding search
            sources = [
                {
                    "name": "techcrunch_funding",
                    "type": "rss",
                    "url": "https://techcrunch.com/category/funding/feed/",
                },
            ]

        session = get_http_session()
        last_run = self.get_last_run_time(conn)
        since_date = last_run - timedelta(hours=1) if last_run else datetime.now(timezone.utc) - timedelta(days=7)

        cursor = conn.cursor()

        for source in sources:
            source_name = source.get("name", "unknown")
            source_type = source.get("type", "rss")
            url = source.get("url", "")

            if source_type == "rss" and url:
                try:
                    resp = session.get(url, timeout=20)
                    resp.raise_for_status()
                except Exception as e:
                    result.errors.append(f"Funding source fetch failed ({source_name}): {e}")
                    continue

                feed = feedparser.parse(resp.text)
                if feed.bozo and not feed.entries:
                    continue

                for entry in feed.entries:
                    try:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        summary = entry.get("summary", "")

                        if not link or not title:
                            continue

                        if published:
                            try:
                                pub_date = datetime.strptime(
                                    published, "%a, %d %b %Y %H:%M:%S %z"
                                )
                                if pub_date < since_date:
                                    result.records_skipped += 1
                                    continue
                            except ValueError:
                                pass

                        if dedup_news_article(conn, link):
                            result.records_skipped += 1
                            continue

                        text = f"{title} {summary}"
                        company_name = self._extract_company(title)
                        round_type = self._extract_round_type(text)
                        amount = self._extract_amount(text)

                        cursor.execute(
                            """INSERT IGNORE INTO funding_events
                               (company_name, round_type, amount_usd, investors_json,
                                announced_date, source, collected_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (
                                company_name or "Unknown",
                                round_type,
                                amount,
                                None,  # investors_json — enriched later
                                published[:10] if published else None,
                                source_name,
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )

                        # Insert into raw_signals with high raw_score
                        raw_score = min(100, 50 + (amount / 1_000_000 if amount else 0))
                        raw_score = min(raw_score, 100)

                        cursor.execute(
                            """INSERT IGNORE INTO raw_signals
                               (signal_type, source_name, source_url, title, body_text,
                                entity_name, published_at, collected_at, processed)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                            (
                                "funding_round",
                                f"funding_{source_name}",
                                link,
                                title,
                                summary[:10000] if summary else None,
                                company_name or "Unknown",
                                published[:26] if published else None,
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )

                        result.records_inserted += 1
                        result.records_collected += 1

                        if amount and amount >= 5_000_000:
                            _logger.info(
                                "💰 FUNDING: %s raised %s (%s)",
                                company_name or "Unknown",
                                self._format_amount(amount),
                                round_type or "unknown round",
                            )

                    except Exception as e:
                        result.errors.append(f"Error processing funding entry: {e}")

        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result

    def _extract_company(self, title: str) -> str | None:
        """Extract company name from funding headline."""
        # Pattern: "Company Raises $Xm Series A" or "$Xm Round for Company"
        match = re.match(r"^([A-Z][A-Za-z0-9 ]{2,40}?)(?:\s+Raises|\s+Raised|\s+Closes|\s+Announces)", title)
        if match:
            return match.group(1).strip()
        # Pattern: "Company lands $Xm..."
        match = re.match(r"^([A-Z][A-Za-z0-9 ]{2,40}?)(?:\s+lands|\s+secures|\s+gets)", title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_round_type(self, text: str) -> str | None:
        """Extract funding round type from text."""
        match = _ROUND_TYPE_PATTERN.search(text)
        if match:
            return match.group(0).title()
        return None

    def _extract_amount(self, text: str) -> int | None:
        """Extract funding amount in USD from text."""
        match = _AMOUNT_PATTERN.search(text)
        if not match:
            return None

        try:
            amount = float(match.group(1).replace(",", ""))
            multiplier = match.group(2)

            if multiplier and multiplier.lower() in ("billion", "b"):
                amount *= 1_000_000_000
            elif multiplier and multiplier.lower() in ("million", "m"):
                amount *= 1_000_000
            elif multiplier and multiplier.lower() in ("k", "thousand"):
                amount *= 1_000

            return int(amount)
        except (ValueError, TypeError):
            return None

    def _format_amount(self, amount: int) -> str:
        """Format amount for logging."""
        if amount >= 1_000_000_000:
            return f"${amount / 1_000_000_000:.1f}B"
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        if amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        return f"${amount}"
