"""TechCrunch RSS collector for startup news."""

import logging
import re
from datetime import datetime, timezone

import feedparser

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session
from db.dedup import dedup_news_article

_logger = logging.getLogger(__name__)

_FUNDING_PATTERN = re.compile(r"\$(\d+(?:\.\d+)?)\s*([BMK])", re.IGNORECASE)
_STARTUP_NAME_PATTERN = re.compile(r"^([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,2})")


class TechCrunchRSSCollector(BaseCollector):
    """Collects startup news from TechCrunch RSS feed."""

    @property
    def name(self) -> str:
        return "techcrunch_rss"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        rss_config = self.config.get("rss", {}).get("techcrunch", {})
        feed_url = rss_config.get("url", "https://techcrunch.com/startups/feed/")
        classify_config = self.config.get("classification", {})

        mfg_keywords = set(kw.lower() for kw in classify_config.get("manufacturing_keywords", []))
        failure_keywords = set(kw.lower() for kw in classify_config.get("failure_keywords", []))

        session = get_http_session()

        _logger.info("Fetching TechCrunch RSS: %s", feed_url)

        try:
            resp = session.get(feed_url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            result.errors.append(f"Failed to fetch TechCrunch RSS: {e}")
            result.status = "failed"
            return result

        feed = feedparser.parse(resp.text)

        if feed.bozo and not feed.entries:
            result.errors.append(f"TechCrunch RSS parse error: {feed.bozo_exception}")
            result.status = "failed"
            return result

        for entry in feed.entries:
            article_url = entry.get("link", "")

            if dedup_news_article(conn, article_url):
                result.records_skipped += 1
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "") or ""
            # TechCrunch uses content:encoded for richer excerpts
            content = entry.get("content", [{}])
            content_text = content[0].get("value", "") if content else ""
            published = entry.get("published", "")

            # Extract categories/tags
            tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]

            # Classify
            combined_text = f"{title} {summary} {' '.join(tags)}".lower()
            is_mfg = 1 if any(kw in combined_text for kw in mfg_keywords) else 0
            mentions_fail = 1 if any(kw in combined_text for kw in failure_keywords) else 0

            # Extract startup name (first capitalized phrase in title)
            startup_name = None
            if mentions_fail:
                match = _STARTUP_NAME_PATTERN.match(title)
                if match:
                    startup_name = match.group(1).strip()

            # Extract funding amount from content
            funding_match = _FUNDING_PATTERN.search(content_text[:2000])

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

            source_name = "TechCrunch"
            display_summary = summary[:500] if summary else content_text[:500]
            if funding_match:
                display_summary = f"[Funding: ${funding_match.group(1)}{funding_match.group(2)}] {display_summary}"

            if not self.dry_run:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO news_articles
                       (title, url, source_name, source_feed, published_at, summary,
                        is_manufacturing, mentions_failure, startup_name_extracted)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (title, article_url, source_name, "techcrunch",
                     pub_at, display_summary,
                     is_mfg, mentions_fail, startup_name),
                )
                cursor.close()
                conn.commit()

            result.records_collected += 1
            result.records_inserted += 1

        result.status = "partial" if result.errors else "success"
        return result
