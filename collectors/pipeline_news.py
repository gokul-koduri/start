"""Collector for pipeline industry news and company updates."""

import logging
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)


# Pipeline-related search terms / keywords
PIPELINE_KEYWORDS = [
    "pipeline inspection",
    "pipeline monitoring",
    "pipeline integrity",
    "smart pigging",
    "pipeline corrosion",
    "leak detection pipeline",
    "inline inspection",
    "pipeline management",
    "MFL inspection",
    "pipeline automation",
    "pipeline failure",
    "pipeline shutdown",
    "pipeline startup funding",
]


class PipelineNewsCollector(BaseCollector):
    """Collects news about pipeline operations companies and technologies."""

    @property
    def name(self) -> str:
        return "pipeline_news"

    def collect(self, conn) -> CollectionResult:
        """Collect pipeline-related news via Google News search."""
        result = CollectionResult(collector_name=self.name)
        session = get_http_session(user_agent="StartupResearchBot/1.0 (+pipeline)")

        collect_config = self.config.get("collectors", {}).get("pipeline_news", {})
        max_articles = collect_config.get("max_articles_per_keyword", 10)
        delay_seconds = collect_config.get("delay_seconds", 2)

        # Process each keyword
        for keyword in PIPELINE_KEYWORDS:
            _logger.info("Searching news for: %s", keyword)

            search_url = f"https://www.google.com/search?q={quote(keyword)}+pipeline&tbm=nws&num={max_articles}"

            try:
                resp = session.get(search_url, timeout=15)
                if resp.status_code == 429:
                    result.errors.append(f"Rate limited on keyword: {keyword}")
                    result.status = "partial"
                    time.sleep(5)
                    continue
                if resp.status_code != 200:
                    result.errors.append(f"HTTP {resp.status_code} for keyword: {keyword}")
                    continue
            except Exception as e:
                result.errors.append(f"Failed to fetch {keyword}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            articles = self._parse_google_news(soup)

            for article in articles:
                if self._insert_article(conn, article, keyword):
                    result.records_inserted += 1
                result.records_collected += 1

            # Rate limiting
            time.sleep(delay_seconds)

        return result

    def _parse_google_news(self, soup) -> list[dict]:
        """Parse Google News search results for article data."""
        articles = []

        for item in soup.select("div.SoaBEf"):
            try:
                title_elem = item.select_one("div.MBeuO")
                link_elem = item.select_one("a")
                source_elem = item.select_one("div.CEMjEng span")
                date_elem = item.select_one("div.OSrXXb span")
                desc_elem = item.select_one("div.GI74Re")

                if not title_elem or not link_elem:
                    continue

                url = link_elem.get("href", "")
                if not url or not url.startswith("http"):
                    continue

                article = {
                    "title": title_elem.get_text(strip=True),
                    "url": url,
                    "source": source_elem.get_text(strip=True) if source_elem else "Unknown",
                    "date": date_elem.get_text(strip=True) if date_elem else "",
                    "description": desc_elem.get_text(strip=True) if desc_elem else "",
                }
                articles.append(article)
            except Exception as e:
                _logger.debug("Failed to parse article: %s", e)
                continue

        return articles

    def _insert_article(self, conn, article: dict, keyword: str) -> bool:
        """Insert article into the database."""
        title = article.get("title", "")
        url = article.get("url", "")
        source = article.get("source", "")
        date_str = article.get("date", "")
        body_text = article.get("description", "")

        # Check for duplicates
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM news_articles WHERE url = %s",
            (url[:2048],),
        )
        if cursor.fetchone():
            cursor.close()
            return False

        # Mark as pipeline-related
        is_manufacturing = 1 if self._is_manufacturing_context(body_text) else 0
        mentions_failure = 1 if self._mentions_failure(body_text) else 0

        cursor.execute(
            """INSERT INTO news_articles
               (title, url, source_name, source_feed, published_at, summary, is_manufacturing, mentions_failure)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (title, url, source, f"pipeline_news:{keyword}", date_str, body_text, is_manufacturing, mentions_failure),
        )
        cursor.close()
        return True

    def _is_manufacturing_context(self, text: str) -> int:
        """Check if article is about manufacturing-related pipeline activity."""
        mfg_terms = [
            "manufacturing", "fabrication", "construction", "installation",
            "OEM", " supplier", "welding", "coating", "corrosion",
        ]
        text_lower = text.lower()
        return 1 if any(term in text_lower for term in mfg_terms) else 0

    def _mentions_failure(self, text: str) -> int:
        """Check if article mentions failures or shutdowns."""
        failure_terms = [
            "failure", "shutdown", "bankruptcy", "closed", "defunct",
            "ceased", "insolvent", "liquidation",
        ]
        text_lower = text.lower()
        return 1 if any(term in text_lower for term in failure_terms) else 0


# CLI runner for testing
if __name__ == "__main__":
    from config import setup_logging, load_config

    setup_logging()
    load_config()

    from db.connection import get_connection
    from db import schema

    conn = get_connection()
    schema.init_schema(conn)

    collector = PipelineNewsCollector()
    result = collector.collect(conn)

    print(f"Collected {result.records_collected} articles")
    print(f"Inserted {result.records_inserted} new articles")
    print(f"Skipped {result.records_skipped} duplicates")
    if result.errors:
        print(f"Errors: {result.errors}")