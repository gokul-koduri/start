"""Twitter/X collector — collects tweets via Nitter RSS feeds.

Data source: Nitter RSS proxy endpoints (Atom XML feeds).
No Twitter API key required — uses public RSS aggregation.

Collects startup-related tweets, founder activity, and product announcements.
Writes to existing raw_signals + social_posts tables (no new schema table).
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_NS = {"atom": "http://www.w3.org/2005/Atom"}

# Signal keywords for startup-related tweets
_SIGNAL_KEYWORDS = {
    "funding": [
        "raised",
        "funding",
        "series a",
        "series b",
        "seed round",
        "investment",
        "vc funding",
    ],
    "launch": [
        "launching",
        "now available",
        "public beta",
        "early access",
        "just launched",
        "new product",
    ],
    "hiring": ["we're hiring", "hiring", "looking for", "join us"],
    "acquisition": ["acquired", "acquisition", "buys", "merger"],
}

# Hashtags relevant to startup signals
_RELEVANT_HASHTAGS = {
    "#startup",
    "#funding",
    "#launch",
    "#saas",
    "#ai",
    "#machinelearning",
    "#venturecapital",
}


class TwitterCollector(BaseCollector):
    """Collects tweets from Nitter RSS feeds.

    Searches for tweets matching configurable queries via Nitter instances.
    Parses Atom XML responses and extracts tweet metadata.

    Config options:
        twitter.nitter_instances: list of Nitter base URLs
        twitter.search_queries: list of search terms
        twitter.timeout_seconds: HTTP timeout (default: 15)
        twitter.min_delay_seconds: delay between requests (default: 3)
    """

    @property
    def name(self) -> str:
        return "twitter"

    def _fetch_feed(
        self, session, instance_url: str, query: str, timeout: int = 15
    ) -> list[dict]:
        """Fetch Nitter RSS feed for a search query."""
        # Nitter search RSS format: /search?f=tweets&q={query}&rss=1
        url = f"{instance_url}/search?f=tweets&q={query}&rss=1"

        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
        except Exception as e:
            _logger.warning("TwitterCollector: feed fetch failed for %s — %s", url, e)
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as e:
            _logger.warning("TwitterCollector: XML parse failed — %s", e)
            return []

        entries = []
        for entry in root.findall("atom:entry", _NS):
            tweet = self._parse_entry(entry)
            if tweet:
                entries.append(tweet)

        return entries

    def _parse_entry(self, entry: ET.Element) -> dict | None:
        """Extract tweet metadata from an Atom entry element."""
        # Title format: "@user: Tweet text here"
        title = entry.findtext("atom:title", default="", namespaces=_NS).strip()

        if not title:
            return None

        # Extract author from title prefix (@username:)
        author = ""
        text = title
        match = re.match(r"^(@[\w]+):\s*(.+)$", title, re.DOTALL)
        if match:
            author = match.group(1)
            text = match.group(2).strip()
        else:
            # Try atom:author
            author_elem = entry.find("atom:author", _NS)
            if author_elem is not None:
                author = author_elem.findtext("atom:name", default="", namespaces=_NS)

        # Published date
        published = entry.findtext("atom:published", default="", namespaces=_NS)
        published_date = self._parse_iso_date(published)

        # Tweet URL from link
        tweet_url = ""
        for link in entry.findall("atom:link", _NS):
            href = link.get("href", "")
            if href and "/status/" in href:
                tweet_url = href
                break
        if not tweet_url:
            # Fallback to entry id
            entry_id = entry.findtext("atom:id", default="", namespaces=_NS)
            if "status/" in entry_id:
                tweet_url = entry_id

        return {
            "author": author,
            "text": text,
            "published_date": published_date,
            "url": tweet_url,
        }

    def _parse_iso_date(self, date_str: str) -> str | None:
        """Parse ISO date string to YYYY-MM-DD format."""
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _find_signals(self, text: str) -> list[dict]:
        """Find startup signal keywords in tweet text."""
        text_lower = text.lower()
        signals = []
        seen = set()

        for category, keywords in _SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() not in seen and kw.lower() in text_lower:
                    signals.append({"keyword": kw, "category": category})
                    seen.add(kw.lower())

        return signals

    def _find_hashtags(self, text: str) -> list[str]:
        """Extract relevant hashtags from tweet text."""
        tags = re.findall(r"#(\w+)", text.lower())
        return [f"#{t}" for t in tags if f"#{t}" in _RELEVANT_HASHTAGS]

    def _find_entity(self, text: str) -> str:
        """Extract a potential company/entity name from tweet text."""
        # Look for @mentions of companies (capitalized usernames)
        mentions = re.findall(r"@(\w+)", text)
        for m in mentions:
            if m[0].isupper() and len(m) > 3:
                return f"@{m}"
        # Look for quoted company names
        quoted = re.findall(r'"([A-Z][A-Za-z\s&]+)"', text)
        if quoted:
            return quoted[0].strip()
        return ""

    def _compute_score(
        self, tweet: dict, signals: list[dict], hashtags: list[str]
    ) -> float:
        """Compute signal strength (0-100).

        Factors:
          - Signal keywords found: +30
          - Recent (< 24h): +25, < 72h: +15
          - Relevant hashtags: +10 per tag, max 20
          - Entity mention in text: +15
          - Capped at 100
        """
        score = 0.0

        # Signal keywords
        if signals:
            score += 30

        # Recency
        pub_str = tweet.get("published_date")
        if pub_str:
            try:
                pub_dt = datetime.strptime(pub_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                age_hours = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
                if age_hours < 24:
                    score += 25
                elif age_hours < 72:
                    score += 15
            except (ValueError, TypeError):
                pass

        # Hashtags
        if hashtags:
            score += min(len(hashtags) * 10, 20)

        # Entity mention
        entity = self._find_entity(tweet.get("text", ""))
        if entity:
            score += 15

        return min(score, 100.0)

    def _insert_tweet(
        self,
        cursor,
        tweet: dict,
        search_term: str,
        signals: list[dict],
        hashtags: list[str],
        raw_score: float,
        result: CollectionResult,
    ) -> None:
        """Insert tweet into social_posts + raw_signals tables."""
        author = tweet["author"]
        text = tweet["text"]
        published_date = tweet["published_date"]
        url = tweet["url"]

        # Insert into social_posts
        cursor.execute(
            """INSERT IGNORE INTO social_posts
               (platform, post_id, author, content, likes, comments,
                shares, posted_at, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                "twitter",
                url or f"tw-{hash(text)}",
                author,
                text,
                0,
                0,
                0,  # No engagement metrics from Nitter RSS
                published_date,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Insert into raw_signals
        signal_keywords = [s["keyword"] for s in signals]
        signal_title = (
            f"{author}: {text[:100]}..." if len(text) > 100 else f"{author}: {text}"
        )

        cursor.execute(
            """INSERT IGNORE INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at, collected_at, processed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
            (
                "twitter",
                "twitter",
                url,
                signal_title,
                text[:500] if text else "",
                author,
                published_date,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "twitter",
            title=signal_title,
            entity_name=author,
            source_url=url,
            body_text=text[:300] if text else "",
            raw_score=raw_score,
            signal_keywords=signal_keywords,
            hashtags=hashtags,
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("twitter", {})

        if self.dry_run:
            result.status = "success"
            return result

        nitter_instances = config.get("nitter_instances", [])
        search_queries = config.get(
            "search_queries",
            [
                "startup funding",
                "new product launch",
                "series A",
            ],
        )
        timeout = config.get("timeout_seconds", 15)
        min_delay = config.get("min_delay_seconds", 3)

        if not nitter_instances or not search_queries:
            _logger.info("TwitterCollector: no instances or queries configured")
            result.status = "partial"
            return result

        session = get_http_session(timeout=timeout)
        session.headers["Accept"] = "application/xml"

        cursor = conn.cursor()

        for query in search_queries:
            for instance in nitter_instances:
                entries = self._fetch_feed(session, instance, query, timeout)

                for tweet in entries:
                    signals = self._find_signals(tweet["text"])
                    hashtags = self._find_hashtags(tweet["text"])
                    raw_score = self._compute_score(tweet, signals, hashtags)

                    try:
                        self._insert_tweet(
                            cursor,
                            tweet,
                            query,
                            signals,
                            hashtags,
                            raw_score,
                            result,
                        )
                    except Exception as e:
                        result.errors.append(
                            f"Error inserting tweet from {instance}: {e}"
                        )

                time.sleep(min_delay)

            _logger.info(
                "TwitterCollector: query '%s' → %d tweets across %d instances",
                query,
                result.records_collected,
                len(nitter_instances),
            )

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
