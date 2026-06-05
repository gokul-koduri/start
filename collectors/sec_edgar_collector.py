"""SEC EDGAR filings collector.

Collects corporate filings (10-K, 10-Q, 8-K, S-1) from the SEC's EDGAR system
to identify financial health signals, M&A activity, executive changes, and
strategic shifts.

Data source: SEC EDGAR RSS feeds (public, no API key required)
Rate limits: 10 requests per second (SEC guideline)
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser

from collectors.base import BaseCollector, CollectionResult
from db.dedup import dedup_news_article
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

# SEC EDGAR full-text search RSS base URL
_EDGAR_RSS_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"
_FILING_TYPES = ["10-K", "10-Q", "8-K", "S-1", "DEF 14A"]


class SECEdgarCollector(BaseCollector):
    """Collects SEC filings for tracked entities and sector keywords."""

    @property
    def name(self) -> str:
        return "sec_edgar"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        sec_config = self.config.get("sec_edgar", {})
        queries = sec_config.get("queries", [])

        if not queries:
            queries = [
                {"company": "", "filing_type": "8-K", "count": 40},
            ]

        session = get_http_session()
        session.headers.update({
            "User-Agent": "OpportunityIntel/1.0 research@example.com",
            "Accept": "application/rss+xml",
        })

        last_run = self.get_last_run_time(conn)
        since_date = last_run - timedelta(hours=1) if last_run else datetime.now(timezone.utc) - timedelta(days=7)

        cursor = conn.cursor()

        for query_config in queries:
            company = query_config.get("company", "")
            filing_type = query_config.get("filing_type", "8-K")
            count = query_config.get("count", 40)

            try:
                params = {
                    "action": "getcurrent",
                    "type": filing_type,
                    "company": company,
                    "dateb": "",
                    "owner": "include",
                    "count": str(count),
                    "output": "atom",
                }

                resp = session.get(_EDGAR_RSS_BASE, params=params, timeout=30)
                resp.raise_for_status()

            except Exception as e:
                result.errors.append(f"SEC EDGAR fetch failed ({filing_type}): {e}")
                _logger.warning("SEC fetch failed: %s", e)
                continue

            feed = feedparser.parse(resp.text)
            if feed.bozo and not feed.entries:
                continue

            for entry in feed.entries:
                try:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")

                    if not link or not title:
                        continue

                    # Skip if before our lookback window
                    if published:
                        try:
                            pub_date = datetime.strptime(
                                published, "%Y-%m-%dT%H:%M:%S%z"
                            )
                            if pub_date < since_date:
                                result.records_skipped += 1
                                continue
                        except ValueError:
                            pass

                    # Dedup by URL
                    if dedup_news_article(conn, link):
                        result.records_skipped += 1
                        continue

                    # Extract company name from title
                    company_name = self._extract_company_name(title)

                    # Extract filing type from title
                    extracted_type = self._extract_filing_type(title)

                    # Compute sentiment (basic keyword heuristic)
                    sentiment = self._basic_sentiment(summary)

                    cursor.execute(
                        """INSERT IGNORE INTO sec_filings
                           (company_name, filing_type, filed_date, document_url,
                            summary_text, sentiment_score, collected_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            company_name or "Unknown",
                            extracted_type or filing_type,
                            published[:10] if published else None,
                            link,
                            summary[:5000] if summary else title,
                            sentiment,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    # Also insert into raw_signals for the scoring pipeline
                    cursor.execute(
                        """INSERT IGNORE INTO raw_signals
                           (signal_type, source_name, source_url, title, body_text,
                            entity_name, published_at, collected_at, processed)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                        (
                            "sec_filing",
                            "sec_edgar",
                            link,
                            title,
                            summary[:10000] if summary else None,
                            company_name or "Unknown",
                            published[:26] if published else None,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    # Publish to Kafka for real-time stream processing
                    self.publish_signal(
                        "sec_filing",
                        title=title,
                        entity_name=company_name or "Unknown",
                        source_url=link,
                        body_text=(summary or "")[:10000],
                        raw_score=60.0,
                        filing_type=filing_type,
                    )

                    result.records_inserted += 1
                    result.records_collected += 1

                except Exception as e:
                    result.errors.append(f"Error processing SEC entry: {e}")
                    _logger.warning("SEC entry error: %s", e)

        cursor.close()
        conn.commit()

        if result.records_inserted > 0:
            result.status = "success"
        elif result.records_skipped > 0:
            result.status = "partial"
        else:
            result.status = "success"  # No new filings is still success

        return result

    def _extract_company_name(self, title: str) -> str | None:
        """Extract company name from SEC filing title."""
        # Pattern: "COMPANY NAME - 8-K" or "COMPANY NAME (CIK: 0001234567)"
        match = re.match(r"^([^(<]+?)(?:\s*[-–]\s*|\s*\()", title.strip())
        if match:
            name = match.group(1).strip()
            # Remove common suffixes
            for suffix in [", Inc.", ", LLC", ", Corp.", ", Ltd."]:
                name = name.replace(suffix, "")
            return name.strip() or None
        return None

    def _extract_filing_type(self, title: str) -> str | None:
        """Extract filing type from title."""
        for ft in _FILING_TYPES:
            if ft.lower() in title.lower():
                return ft
        return None

    def _basic_sentiment(self, text: str) -> float:
        """Basic keyword-based sentiment scoring for filing text.

        Returns a float between -1.0 (negative) and 1.0 (positive).
        Used as a quick signal before full NLP processing in Phase 2.
        """
        if not text:
            return 0.0

        positive_keywords = {
            "growth", "increase", "revenue", "profit", "record", "strong",
            "innovation", "expand", "acquisition", "strategic", "upgraded",
        }
        negative_keywords = {
            "loss", "decline", "risk", "litigation", "bankruptcy", "fraud",
            "restatement", "investigation", "material weakness", "downgrade",
            "impairment", "layoff", "restructure",
        }

        words = set(text.lower().split())
        pos_count = len(words & positive_keywords)
        neg_count = len(words & negative_keywords)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        return round((pos_count - neg_count) / total, 4)
