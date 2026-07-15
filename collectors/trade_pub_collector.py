"""Trade Publication Scraper for Manufacturing Industry Sources.

Collects articles from manufacturing trade publications covering:
  - Industry Week, Manufacturing Engineering (pennwell.com)
  - Modern Machine Shop, Production Machining (various)
  - Plant Engineering, Reliability Magazine
  - Oil & Gas Journal, Pipeline & Gas Journal
  - Food Manufacturing, Pharmaceutical Engineering

Data source: RSS feeds and web scraping from trade publication sites
"""

import logging
from datetime import datetime, timezone
import re

from bs4 import BeautifulSoup
from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

# Trade Publication RSS Feeds and Configuration
TRADE_PUBLICATIONS = [
    {
        "name": "Industry Week",
        "url": "https://www.industryweek.com/rss",
        "feed_type": "rss",
    },
    {
        "name": "Modern Machine Shop",
        "url": "https://www.mmsforst.com/rss",
        "feed_type": "rss",
    },
    {
        "name": "Plant Engineering",
        "url": "https://www.plantengineering.com/rss",
        "feed_type": "rss",
    },
    {
        "name": "Oil & Gas Journal",
        "url": "https://www.ogj.com/rss",
        "feed_type": "rss",
    },
    {
        "name": "Food Manufacturing",
        "url": "https://www.foodengineeringmag.com/rss",
        "feed_type": "rss",
    },
    {
        "name": "Pharmaceutical Engineering",
        "url": "https://www.ispe.org/pharmaceutical-engineering/feed",
        "feed_type": "rss",
    },
    {
        "name": "Reliability Magazine",
        "url": "https://reliability.com/rss/",
        "feed_type": "rss",
    },
    {
        "name": "The Fabricator",
        "url": "https://www.thefabricator.com/rss",
        "feed_type": "rss",
    },
    # Manufacturing Executive and other recent additions
    {
        "name": "Manufacturing Tomorrow",
        "url": "https://www.manufacturingtomorrow.com/rss",
        "feed_type": "rss",
    },
    {
        "name": "American Machinist",
        "url": "https://www.amtonline.com/rss",
        "feed_type": "rss",
    },
]

# Keywords that indicate manufacturing and pipeline-specific content
RELEVANCE_KEYWORDS = [
    "manufacturing", "factory", "production", "automation",
    "robotics", "machining", "cnc", "metalworking",
    "pipeline", "oil gas", "refinery", "petrochemical",
    "corrosion", "inspection", "maintenance", "reliability",
    "supply chain", "reshoring", "nearshoring", "domestic",
    "semiconductor", "ev battery", "solar manufacturing",
    "industrial", "machinery", "equipment",
    "quality control", "lean manufacturing", "six sigma",
    "additive manufacturing", "3d printing",
    "welding", "fabrication", "machining",
    "process improvement", "digital transformation",
    "smart factory", "industry 4.0", "iiot",
]


class TradePublicationCollector(BaseCollector):
    """Collects articles from manufacturing trade publications."""

    @property
    def name(self) -> str:
        return "trade_publications"

    def _is_relevant_article(self, title: str, description: str = "") -> bool:
        """Check if article is relevant to manufacturing/pipeline focus."""
        text = (title + " " + description).lower()
        for keyword in RELEVANCE_KEYWORDS:
            if keyword in text:
                return True
        return False

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        session = get_http_session(user_agent="StartupResearchBot/1.0")

        cursor = conn.cursor()

        # Get recent articles from each publication
        for pub in TRADE_PUBLICATIONS:
            publication_name = pub["name"]
            feed_url = pub["url"]

            try:
                _logger.info("Fetching %s feed...", publication_name)
                resp = session.get(feed_url, timeout=30)

                if resp.status_code != 200:
                    result.errors.append(
                        f"{publication_name}: HTTP {resp.status_code}"
                    )
                    continue

                content = resp.text

                # Try to parse as RSS/Atom
                articles = self._parse_rss(content, publication_name)

                if not articles:
                    # Try to extract from HTML if RSS parsing fails
                    articles = self._parse_html(content, publication_name)

                for article in articles:
                    try:
                        # Check relevance
                        if not self._is_relevant_article(
                            article.get("title", ""),
                            article.get("description", "")
                        ):
                            continue

                        cursor.execute(
                            """INSERT INTO news_articles
                               (title, url, source_name, source_feed, published_at,
                                summary, is_manufacturing, mentions_failure,
                                collected_at)
                               VALUES (%s, %s, %s, %s, %s, %s, 1, 0, %s)
                               ON DUPLICATE KEY UPDATE
                                 title = VALUES(title),
                                 summary = VALUES(summary)""",
                            (
                                article.get("title", "")[:500],
                                article.get("url", "")[:2048],
                                publication_name,
                                feed_url,
                                article.get("published", "")[:50],
                                article.get("description", "")[:5000],
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )

                        # Also insert into raw_signals for signal processing
                        cursor.execute(
                            """INSERT IGNORE INTO raw_signals
                               (signal_type, source_name, source_url, title, body_text,
                                entity_name, published_at, collected_at, processed)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                            (
                                "news_mention",
                                publication_name,
                                article.get("url", "")[:2048],
                                article.get("title", "")[:500],
                                article.get("description", "")[:5000],
                                self._extract_company_name(article.get("title", "")),
                                article.get("published", "")[:50],
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )

                        result.records_collected += 1

                    except Exception as e:
                        _logger.debug(
                            "Error processing article from %s: %s",
                            publication_name,
                            e
                        )

                if articles:
                    result.records_inserted += len(articles)

            except Exception as e:
                result.errors.append(f"{publication_name}: {str(e)[:100]}")
                _logger.warning("Failed to collect from %s: %s", publication_name, e)

        cursor.close()
        conn.commit()

        result.status = "success" if result.records_inserted > 0 else "partial"
        return result

    def _parse_rss(self, content: str, source: str) -> list[dict]:
        """Parse RSS/Atom feed content."""
        articles = []

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Try RSS items
            items = soup.find_all("item")

            # Try Atom entries
            if not items:
                items = soup.find_all("entry")

            for item in items:
                title = self._get_tag_text(item, "title")
                link = self._get_tag_text(item, "link")

                # Handle Atom link that might be in href attribute
                if not link:
                    link_tag = item.find("link")
                    if link_tag and link_tag.get("href"):
                        link = link_tag.get("href")
                    elif link_tag:
                        link = link_tag.text or link_tag.string

                pub_date = (
                    self._get_tag_text(item, "pubDate")
                    or self._get_tag_text(item, "published")
                    or self._get_tag_text(item, "updated")
                    or self._get_tag_text(item, "dc:date")
                )

                description = (
                    self._get_tag_text(item, "description")
                    or self._get_tag_text(item, "content:encoded")
                    or self._get_tag_text(item, "content")
                    or self._get_tag_text(item, "summary")
                    or ""
                )

                # Clean HTML from description
                desc_soup = BeautifulSoup(description, "html.parser")
                description = desc_soup.get_text(separator=" ", strip=True)

                if title and link:
                    articles.append({
                        "title": title.strip(),
                        "url": link.strip(),
                        "published": self._normalize_date(pub_date),
                        "description": description.strip()[:5000],
                        "source": source,
                    })

        except Exception as e:
            _logger.debug("RSS parsing failed for %s: %s", source, e)

        return articles

    def _parse_html(self, content: str, source: str) -> list[dict]:
        """Fallback: Parse HTML content for articles."""
        articles = []

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Look for common article list patterns
            article_links = soup.find_all("a", href=True)

            for link_tag in article_links[:30]:  # Limit to first 30
                href = link_tag.get("href", "")
                title = link_tag.get_text(strip=True)

                # Skip if link doesn't look like an article
                if len(title) < 10 or len(href) < 10:
                    continue

                # Skip navigation links
                skip_patterns = ["about", "contact", "subscribe", "login",
                               "register", "privacy", "terms", "rss", "feed"]
                if any(p in href.lower() for p in skip_patterns):
                    continue

                # Normalize URL
                if href.startswith("/"):
                    from urllib.parse import urljoin
                    href = urljoin(f"https://{source}/", href)

                articles.append({
                    "title": title,
                    "url": href,
                    "published": "",
                    "description": "",
                    "source": source,
                })

        except Exception as e:
            _logger.debug("HTML parsing failed for %s: %s", source, e)

        return articles

    def _get_tag_text(self, parent, tag_name: str) -> str:
        """Get text content of a tag, handling namespaced tags."""
        tag = parent.find(tag_name)
        if tag:
            return tag.get_text(strip=True)
        # Try with namespace
        tag = parent.find(tag_name.replace(":", ":"))
        if tag:
            return tag.get_text(strip=True)
        return ""

    def _normalize_date(self, date_str: str) -> str:
        """Normalize various date formats to ISO format."""
        if not date_str:
            return ""

        # Try to parse common date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 (old)
            "%Y-%m-%dT%H:%M:%S%z",      # ISO 8601
            "%Y-%m-%dT%H:%M:%SZ",        # ISO 8601 UTC
            "%Y-%m-%d",                  # Simple date
            "%d %b %Y",                   # 01 Jan 2024
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue

        return date_str  # Return original if parsing fails

    def _extract_company_name(self, title: str) -> str:
        """Extract potential company names from article title."""
        # Look for patterns like "Company Name Announces" or "Company Reports"
        patterns = [
            r"^([A-Z][A-Za-z0-9&' ]+) (announces|reports|launches|reveals|unveils|collaborates)",
            r"^([A-Z][A-Za-z0-9&' ]+) (acquires|acquisition|merges|partners with)",
        ]

        for pattern in patterns:
            match = re.match(pattern, title)
            if match:
                return match.group(1).strip()

        return ""


if __name__ == "__main__":
    collector = TradePublicationCollector()
    result = collector.run()
    print(f"Collected {result.records_collected} articles")
    print(f"Inserted {result.records_inserted}")
    print(f"Errors: {len(result.errors)}")