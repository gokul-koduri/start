"""Newsletter collector — aggregates articles from startup/tech newsletters.

Data source: Configured newsletter/archive URLs scraped via HTTP GET.
Rate limit: Configurable delays between requests.

This collector tracks startup-focused newsletter articles for funding signals,
launches, and market trends mentioned in curated newsletters.
"""

import logging
import re
import time
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

# Startup-related keywords for content filtering
_STARTUP_KEYWORDS = [
    "startup",
    "funding",
    "raised",
    "launched",
    "series a",
    "seed round",
    "venture capital",
    "ipo",
    "acquired",
    "exit",
    "unicorn",
]


class NewsletterCollector(BaseCollector):
    """Collects articles from startup/tech newsletters.

    Scrapes configured newsletter/archive URLs, extracts article metadata,
    and scores based on recency and startup relevance.

    Config options:
        newsletter.enabled: enable/disable collector
        newsletter.sources: list of newsletter URLs to scrape
        newsletter.timeout_seconds: request timeout (default: 15)
        newsletter.min_delay_seconds: delay between requests (default: 2)
    """

    @property
    def name(self) -> str:
        return "newsletter"

    def _fetch_newsletter(self, session, url: str) -> str:
        """Fetch newsletter HTML content from URL."""
        try:
            resp = session.get(
                url,
                timeout=self.config.get("newsletter", {}).get("timeout_seconds", 15),
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            _logger.warning("Newsletter fetch failed: %s — %s", url, e)
            return ""

    def _parse_html(self, html: str) -> dict | None:
        """Extract article metadata from HTML content.

        Uses regex to extract title, content, and metadata.
        This is a simplified parser - assumes newsletter pages have consistent structure.
        """
        if not html:
            return None

        # Extract title from <title> tag or <h1>
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else ""

        if not title:
            h1_match = re.search(
                r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL
            )
            title = h1_match.group(1).strip() if h1_match else ""

        # Clean title (remove HTML tags)
        title = re.sub(r"<[^>]+>", "", title)
        title = title.strip()

        if not title:
            return None

        # Extract main content from <body> or <article>
        body_match = re.search(
            r"<body[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL
        )
        content = body_match.group(1) if body_match else html

        # Remove script and style elements
        content = re.sub(
            r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
        )
        content = re.sub(
            r"<style[^>]*>.*?</style>", "", content, flags=re.IGNORECASE | re.DOTALL
        )

        # Strip HTML tags to get plain text
        content_text = re.sub(r"<[^>]+>", " ", content)
        content_text = " ".join(content_text.split())  # Collapse whitespace
        content_text = content_text.strip()

        # Limit content length
        if len(content_text) > 10000:
            content_text = content_text[:10000]

        # Extract author/source from meta tags or byline patterns
        author = ""
        author_match = re.search(
            r'<meta[^>]*name="author"[^>]*content="([^"]+)"', html, re.IGNORECASE
        )
        if author_match:
            author = author_match.group(1).strip()
        else:
            # Try byline pattern
            byline_match = re.search(
                r"(by|By)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", content_text[:500]
            )
            if byline_match:
                author = byline_match.group(2).strip()

        # Extract publish date from meta tags or article content
        publish_date = None
        date_match = re.search(
            r'<meta[^>]*(name|property)="[^"]*date[^"]*"[^>]*content="([^"]+)"',
            html,
            re.IGNORECASE,
        )
        if date_match:
            date_str = date_match.group(2).strip()
            publish_date = self._parse_date(date_str)

        # Extract source name from URL or domain
        source_name = ""
        if url_match := re.search(r"https?://([^/]+)", html):
            source_name = url_match.group(1).replace("www.", "")

        return {
            "title": title,
            "source_name": source_name,
            "author": author,
            "content_text": content_text,
            "publish_date": publish_date,
        }

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse various date formats to datetime object."""
        if not date_str:
            return None

        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO with timezone
            "%Y-%m-%dT%H:%M:%SZ",  # ISO UTC
            "%Y-%m-%dT%H:%M:%S",  # ISO without timezone
            "%Y-%m-%d",  # Date only
            "%B %d, %Y",  # January 15, 2024
            "%d %B %Y",  # 15 January 2024
            "%m/%d/%Y",  # 01/15/2024
            "%m-%d-%Y",  # 01-15-2024
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                continue

        return None

    def _compute_score(self, article: dict) -> float:
        """Compute signal strength (0-100).

        Factors:
          - Recent publish date (< 7 days): +35
          - Recent (< 30 days): +20
          - Recent (< 90 days): +10
          - Contains startup keywords: +25
          - Long content (> 1000 chars): +10
        """
        score = 0.0

        # Recency bonus
        publish_date = article.get("publish_date")
        if publish_date:
            if isinstance(publish_date, str):
                try:
                    publish_date = datetime.fromisoformat(
                        publish_date.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    publish_date = None

            if publish_date and isinstance(publish_date, datetime):
                if publish_date.tzinfo is None:
                    publish_date = publish_date.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                age_days = (now - publish_date).days

                if age_days < 7:
                    score += 35
                elif age_days < 30:
                    score += 20
                elif age_days < 90:
                    score += 10

        # Startup keyword detection
        content_lower = (article.get("content_text") or "").lower()
        title_lower = (article.get("title") or "").lower()
        combined_text = f"{title_lower} {content_lower}"

        keyword_count = sum(1 for kw in _STARTUP_KEYWORDS if kw in combined_text)
        if keyword_count > 0:
            score += 25

        # Content length signal (indicates in-depth analysis)
        content_length = len(article.get("content_text", ""))
        if content_length > 1000:
            score += 10

        return min(score, 100.0)

    def _insert_article(
        self, cursor, article: dict, url: str, result: CollectionResult
    ) -> None:
        """Insert article into newsletter_articles and raw_signals."""
        title = article["title"]
        source_name = article["source_name"]
        author = article["author"]
        content_text = article["content_text"]
        publish_date = article["publish_date"]

        raw_score = self._compute_score(article)

        # Convert datetime to ISO string for storage
        publish_date_str = None
        if publish_date:
            if isinstance(publish_date, datetime):
                publish_date_str = publish_date.isoformat()
            else:
                publish_date_str = str(publish_date)

        # Insert into newsletter_articles
        cursor.execute(
            """INSERT INTO newsletter_articles
               (title, source_name, author, content_text, publish_date, url, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 title = VALUES(title),
                 author = VALUES(author),
                 content_text = VALUES(content_text),
                 publish_date = VALUES(publish_date),
                 collected_at = VALUES(collected_at)""",
            (
                title,
                source_name or None,
                author or None,
                content_text or None,
                publish_date_str,
                url,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Insert into raw_signals
        cursor.execute(
            """INSERT IGNORE INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at, collected_at, processed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
            (
                "newsletter",
                source_name or "newsletter",
                url,
                title,
                content_text[:500] if content_text else "",
                source_name or "",
                publish_date_str,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "newsletter",
            title=title,
            entity_name=source_name or "",
            source_url=url,
            body_text=content_text[:300] if content_text else "",
            raw_score=raw_score,
            author=author,
            source_name=source_name,
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("newsletter", {})

        if self.dry_run:
            result.status = "success"
            return result

        sources = config.get("sources", [])
        timeout = config.get("timeout_seconds", 15)
        min_delay = config.get("min_delay_seconds", 2)

        if not sources:
            _logger.warning("NewsletterCollector: No sources configured")
            result.status = "partial"
            return result

        session = get_http_session(timeout=timeout)
        session.headers["Accept"] = "text/html"

        cursor = conn.cursor()

        for url in sources:
            html = self._fetch_newsletter(session, url)
            if not html:
                continue

            article = self._parse_html(html)
            if article:
                try:
                    self._insert_article(cursor, article, url, result)
                except Exception as e:
                    result.errors.append(f"Error inserting article from {url}: {e}")

            time.sleep(min_delay)  # Polite delay

            _logger.info(
                "NewsletterCollector: source '%s' → %s",
                url,
                "article found" if article else "no article",
            )

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
