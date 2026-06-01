"""Google News RSS collector for startup failure articles."""

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session
from db.dedup import dedup_news_article

_logger = logging.getLogger(__name__)

# Regex to extract startup name from headlines like "StartupX failed" or "StartupX shuts down"
_STARTUP_NAME_PATTERN = re.compile(
    r"(?:^|\s)([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,3})\s+"
    r"(?:fails?|shuts? down?|goes? bankrupt|closes?|collapses?|ceases?|shuts down|went under)",
    re.IGNORECASE,
)


class GoogleNewsRSSCollector(BaseCollector):
    """Collects news articles about startup failures from Google News RSS."""

    @property
    def name(self) -> str:
        return "google_news_rss"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        rss_config = self.config.get("rss", {}).get("google_news", {})
        base_url = rss_config.get("base_url", "https://news.google.com/rss/search")
        queries = rss_config.get("queries", [])
        classify_config = self.config.get("classification", {})

        mfg_keywords = set(kw.lower() for kw in classify_config.get("manufacturing_keywords", []))
        failure_keywords = set(kw.lower() for kw in classify_config.get("failure_keywords", []))

        if not queries:
            result.errors.append("No Google News queries configured")
            result.status = "failed"
            return result

        session = get_http_session()

        for query_config in queries:
            query = query_config["query"]
            params = query_config.get("params", "hl=en-US&gl=US&ceid=US:en")

            # Incremental: get most recent article date for this query
            last_date = self._get_last_published(conn)
            after_clause = ""
            if last_date:
                after_clause = f"+after:{last_date.strftime('%Y-%m-%d')}"

            url = f"{base_url}?q={quote_plus(query + after_clause)}&{params}"
            _logger.debug("Google News query: %s", query)

            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                result.errors.append(f"Failed to fetch Google News for '{query}': {e}")
                _logger.warning("Google News fetch failed for '%s': %s", query, e)
                continue

            feed = feedparser.parse(resp.text)

            if feed.bozo and not feed.entries:
                _logger.warning("Google News parse error for '%s': %s", query, feed.bozo_exception)
                continue

            for entry in feed.entries:
                article_url = entry.get("link", "")

                # Dedup
                if dedup_news_article(conn, article_url):
                    result.records_skipped += 1
                    continue

                title = entry.get("title", "")
                summary = entry.get("summary", "")
                published = entry.get("published", "")
                source_name = entry.get("source", {}).get("title", "Google News") if isinstance(entry.get("source"), dict) else "Google News"

                # Classify
                title_lower = title.lower()
                summary_lower = summary.lower()
                combined = f"{title_lower} {summary_lower}"

                is_mfg = 1 if any(kw in combined for kw in mfg_keywords) else 0
                mentions_fail = 1 if any(kw in combined for kw in failure_keywords) else 0

                # Extract startup name
                startup_name = None
                if mentions_fail:
                    match = _STARTUP_NAME_PATTERN.search(title)
                    if match:
                        startup_name = match.group(1).strip()

                # Parse published date
                pub_at = None
                if published:
                    try:
                        parsed = feedparser.parse(published)
                        if hasattr(parsed, "published_parsed") and parsed.published_parsed:
                            dt = datetime(*parsed.published_parsed[:6], tzinfo=timezone.utc)
                            pub_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pub_at = published[:19] if len(published) >= 19 else published

                if not self.dry_run:
                    cursor = conn.cursor()
                    cursor.execute(
                        """INSERT INTO news_articles
                           (title, url, source_name, source_feed, published_at, summary,
                            is_manufacturing, mentions_failure, startup_name_extracted)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (title, article_url, source_name, "google_news",
                         pub_at, summary[:500] if summary else None,
                         is_mfg, mentions_fail, startup_name),
                    )
                    cursor.close()
                    conn.commit()

                result.records_collected += 1
                result.records_inserted += 1

            # Small delay between queries
            import time
            time.sleep(1)

        result.status = "partial" if result.errors else "success"
        return result

    def _get_last_published(self, conn) -> datetime | None:
        """Get the most recent published_at from news_articles."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(published_at) as latest FROM news_articles WHERE source_feed = 'google_news'"
        )
        row = cursor.fetchone()
        cursor.close()
        if row and row["latest"]:
            try:
                return datetime.strptime(row["latest"][:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
        return None
