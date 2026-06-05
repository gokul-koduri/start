"""Social media collector — monitors Reddit and Hacker News for sentiment signals.

Collects posts from configured subreddits (via PRAW) and HN (via Algolia API).
Social signals are the fastest-moving (weight: 5) but noisiest — they
indicate community sentiment, early adoption, and word-of-mouth.

Design choices:
    - Reddit: PRAW (Python Reddit API Wrapper) with configurable subreddits
    - Hacker News: Algolia Search API (free, no auth required)
    - Engagement scoring based on upvotes + comments (normalized)
    - Quick entity extraction via heuristics (no NLP needed for collectors)
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

from collectors.base import BaseCollector, CollectionResult
from ingestion.signal_normalizer import normalize_signal

_logger = logging.getLogger(__name__)


class SocialMediaCollector(BaseCollector):
    """Collects social media signals from Reddit and Hacker News.

    Config options:
        lookback_hours: hours back to search (default: 24)
        reddit.subreddits: list of subreddit names
        reddit.post_limit: max posts per subreddit (default: 100)
        reddit.min_score: minimum post score to include (default: 10)
        hacker_news.queries: list of search queries
        hacker_news.max_results: max HN results per query (default: 50)
    """

    @property
    def name(self) -> str:
        return "social_media"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        cursor = conn.cursor()

        # Collect from Reddit
        try:
            self._collect_reddit(conn, cursor, result)
        except Exception as e:
            _logger.warning("SocialMediaCollector: Reddit collection failed: %s", e)
            result.errors.append(f"Reddit: {e}")

        # Collect from Hacker News
        try:
            self._collect_hacker_news(conn, cursor, result)
        except Exception as e:
            _logger.warning("SocialMediaCollector: HN collection failed: %s", e)
            result.errors.append(f"Hacker News: {e}")

        conn.commit()
        cursor.close()
        result.status = "partial" if result.errors else "success"
        return result

    def _collect_reddit(self, conn, cursor, result: CollectionResult) -> None:
        """Collect posts from configured subreddits via PRAW."""
        reddit_config = self.config.get("reddit", {})
        subreddits = reddit_config.get("subreddits", [])
        post_limit = reddit_config.get("post_limit", 100)
        min_score = reddit_config.get("min_score", 10)

        if not subreddits:
            return

        try:
            import praw
            reddit = praw.Reddit(
                client_id=self.config.get("reddit_client_id", ""),
                client_secret=self.config.get("reddit_client_secret", ""),
                user_agent=self.config.get(
                    "reddit_user_agent", "OpportunityIntel/1.0 (research)",
                ),
            )
        except (ImportError, Exception) as e:
            _logger.warning("SocialMediaCollector: PRAW unavailable: %s", e)
            return

        for subreddit_name in subreddits:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                count = 0
                for submission in subreddit.hot(limit=post_limit):
                    if submission.score < min_score:
                        continue

                    self._insert_reddit_post(
                        cursor, submission, subreddit_name, result,
                    )
                    count += 1

                _logger.info(
                    "SocialMediaCollector: r/%s → %d posts collected",
                    subreddit_name, count,
                )
            except Exception as e:
                _logger.warning(
                    "SocialMediaCollector: r/%s failed: %s", subreddit_name, e,
                )
                result.errors.append(f"r/{subreddit_name}: {e}")

    def _insert_reddit_post(
        self, cursor, submission, subreddit: str, result: CollectionResult,
    ) -> None:
        """Insert a Reddit post into social_posts and raw_signals."""
        entity_name, entity_type = self._extract_entity_from_title(
            submission.title + " " + (submission.selftext[:200] if submission.selftext else ""),
        )

        raw_score = self._compute_engagement_score(
            submission.score, submission.num_comments,
        )

        # Insert into social_posts
        cursor.execute(
            """INSERT INTO social_posts
               (platform, post_id, title, body_text, author, score, num_comments,
                url, subreddit, entity_name, entity_type, published_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE score = VALUES(score), num_comments = VALUES(num_comments)""",
            (
                "reddit", submission.id, submission.title[:1000],
                submission.selftext[:5000] if submission.selftext else "",
                str(submission.author) if submission.author else "[deleted]",
                submission.score, submission.num_comments,
                submission.url, subreddit, entity_name, entity_type,
                datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if submission.created_utc else None,
            ),
        )
        result.records_collected += 1
        result.records_inserted += 1

        # Insert into raw_signals
        signal = normalize_signal(
            signal_type="social_buzz",
            source_name="social_media",
            source_url=f"https://reddit.com{submission.permalink}",
            title=submission.title[:1000],
            body_text=submission.selftext[:50_000] if submission.selftext else "",
            entity_name=entity_name,
            entity_type=entity_type,
            published_at=(
                datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if submission.created_utc else None
            ),
            raw_score=raw_score,
            platform="reddit",
            subreddit=subreddit,
            post_score=submission.score,
            num_comments=submission.num_comments,
        )
        cursor.execute(
            """INSERT INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE title = VALUES(title)""",
            (
                signal.signal_type, signal.source_name, signal.source_url,
                signal.title, signal.body_text, signal.entity_name,
                signal.published_at,
            ),
        )

    def _collect_hacker_news(self, conn, cursor, result: CollectionResult) -> None:
        """Collect posts from Hacker News via Algolia Search API."""
        hn_config = self.config.get("hacker_news", {})
        queries = hn_config.get("queries", [])
        max_results = hn_config.get("max_results", 50)
        lookback_hours = self.config.get("lookback_hours", 24)

        since_timestamp = int(
            (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp(),
        )

        for query in queries:
            try:
                url = (
                    f"https://hn.algolia.com/api/v1/search?"
                    f"query={urllib.request.quote(query)}"
                    f"&tags=story"
                    f"&numericFilters=created_at_i>{since_timestamp}"
                    f"&hitsPerPage={max_results}"
                )

                req = urllib.request.Request(url, headers={
                    "User-Agent": "OpportunityIntel/1.0 (research)",
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())

                hits = data.get("hits", [])
                for hit in hits:
                    self._insert_hn_post(cursor, hit, result)

                _logger.info(
                    "SocialMediaCollector: HN query '%s' → %d posts",
                    query, len(hits),
                )

            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                _logger.warning("SocialMediaCollector: HN query '%s' failed: %s", query, e)
                result.errors.append(f"HN: {query}: {e}")

    def _insert_hn_post(
        self, cursor, hit: dict, result: CollectionResult,
    ) -> None:
        """Insert a Hacker News post into social_posts and raw_signals."""
        title = hit.get("title", "")
        story_text = title + " " + hit.get("story_text", "")[:200]
        entity_name, entity_type = self._extract_entity_from_title(story_text)

        raw_score = self._compute_engagement_score(
            hit.get("points", 0), hit.get("num_comments", 0),
        )

        created_at = None
        if hit.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    hit["created_at"].replace("Z", "+00:00"),
                )
            except (ValueError, TypeError):
                pass

        # Insert into social_posts
        cursor.execute(
            """INSERT INTO social_posts
               (platform, post_id, title, body_text, author, score, num_comments,
                url, entity_name, entity_type, published_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE score = VALUES(score), num_comments = VALUES(num_comments)""",
            (
                "hacker_news", hit.get("objectID", ""),
                title[:1000],
                hit.get("story_text", "")[:5000],
                hit.get("author", ""),
                hit.get("points", 0), hit.get("num_comments", 0),
                hit.get("url", hit.get("story_url", "")),
                entity_name, entity_type, created_at,
            ),
        )
        result.records_collected += 1
        result.records_inserted += 1

        # Insert into raw_signals
        signal = normalize_signal(
            signal_type="social_buzz",
            source_name="social_media",
            source_url=hit.get("url", hit.get("story_url", "")),
            title=title[:1000],
            body_text=hit.get("story_text", "")[:50_000],
            entity_name=entity_name,
            entity_type=entity_type,
            published_at=created_at,
            raw_score=raw_score,
            platform="hacker_news",
        )
        cursor.execute(
            """INSERT INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE title = VALUES(title)""",
            (
                signal.signal_type, signal.source_name, signal.source_url,
                signal.title, signal.body_text, signal.entity_name,
                signal.published_at,
            ),
        )

    def _extract_entity_from_title(self, text: str) -> tuple[str, str]:
        """Quick entity extraction from title text using heuristics.

        Returns (entity_name, entity_type) tuple.
        Uses pattern matching to detect companies mentioned in context.
        """
        # Pattern: "$X raised" → company
        match = re.search(r'\$(\d[\d,.]*)[MmBb]?\b.*?(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b)', text)
        if match:
            return match.group(2).strip(), "company"

        # Pattern: "Company launches/releases/announces"
        match = re.search(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b\s+(?:launches?|releases?|announces?|raises?|debuts?)',
            text,
        )
        if match:
            return match.group(1).strip(), "company"

        # Pattern: title case phrase at start (likely company name)
        match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
        if match and len(match.group(1)) < 40:
            return match.group(1).strip(), "company"

        return "", "company"

    def _compute_engagement_score(self, score: int, comments: int) -> float:
        """Score social media engagement (0-100).

        Reddit: score + (num_comments * 2), capped at 100.
        HN: points + (num_comments * 3), capped at 100.
        """
        raw = score + (comments * 2)
        return min(raw / 10.0, 100.0)  # Normalize: 500+ engagement = max score
