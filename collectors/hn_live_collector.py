"""HN Live collector — real-time Hacker News story and comment monitoring.

Polls the official HN Firebase API for new stories and enriches them with
comments from the Algolia HN API. Complements the batch HN collector in
SocialMediaCollector (which uses Algolia search queries with lookback).

Data sources:
  - Firebase API: /newstories.json + /item/{id}.json (story metadata)
  - Algolia API: /items/{id} (nested comment tree)
Both are free, no authentication required.
"""

import json
import logging
import re
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"
_ALGOLIA_BASE = "https://hn.algolia.com/api/v1"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hn_live_comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    comment_id VARCHAR(20) NOT NULL,
    story_id VARCHAR(20) NOT NULL,
    author VARCHAR(200),
    body_text TEXT,
    score INT DEFAULT 0,
    parent_id VARCHAR(20),
    story_title VARCHAR(1000),
    collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_hn_comment (comment_id)
)
"""


class HNLiveCollector(BaseCollector):
    """Collects new Hacker News stories in near-real-time via Firebase API.

    Unlike the batch HN collector (Algolia search queries), this collector:
      - Polls /newstories.json for all new stories (not query-filtered)
      - Uses get_last_run_time() to only fetch stories since last run
      - Collects top-level comments from high-engagement stories via Algolia
      - Writes to shared social_posts table (platform="hn_live") + hn_live_comments

    Config options:
        hn_live.firebase.base_url: Firebase API base (default: official HN)
        hn_live.algolia.base_url: Algolia API base
        hn_live.max_stories: max stories to process per run (default: 50)
        hn_live.min_points: minimum points for comment collection (default: 5)
        hn_live.comment_limit: top comments to fetch per story (default: 5)
        hn_live.collect_comments: whether to fetch comments (default: true)
    """

    @property
    def name(self) -> str:
        return "hn_live"

    def _compute_score(self, points: int, num_comments: int) -> float:
        """Compute engagement score (0-100).

        HN weighting: points + (num_comments * 3), normalize to 0-100.
        """
        raw = points + (num_comments * 3)
        return min(raw / 10.0, 100.0)

    def _extract_entity(self, text: str) -> tuple[str, str]:
        """Quick entity extraction from text using heuristics."""
        combined = text[:500]

        # "$X raised ... CompanyName"
        match = re.search(
            r'\$(\d[\d,.]*)[MmBb]?\b.*?(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b)',
            combined,
        )
        if match:
            return match.group(2).strip(), "company"

        # "Company launches/releases/announces"
        match = re.search(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b\s+(?:launches?|releases?|announces?|raises?|debuts?)',
            combined,
        )
        if match:
            return match.group(1).strip(), "company"

        # Title case at start
        match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', combined)
        if match and len(match.group(1)) < 40:
            return match.group(1).strip(), "company"

        return "", "company"

    def _fetch_json(self, session, url: str) -> dict | list | None:
        """Fetch JSON from an API endpoint with error handling."""
        try:
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            _logger.warning("HN API fetch failed: %s — %s", url, e)
            return None

    def _fetch_new_story_ids(self, session, firebase_base: str) -> list[int]:
        """Fetch list of new story IDs from Firebase /newstories.json."""
        data = self._fetch_json(session, f"{firebase_base}/newstories.json")
        if isinstance(data, list):
            return data
        return []

    def _fetch_story(self, session, firebase_base: str, story_id: int) -> dict | None:
        """Fetch individual story from Firebase /item/{id}.json."""
        return self._fetch_json(session, f"{firebase_base}/item/{story_id}.json")

    def _fetch_comments(self, session, algolia_base: str,
                        story_id: int, story_title: str,
                        comment_limit: int) -> list[dict]:
        """Fetch top-level comments for a story from Algolia API."""
        data = self._fetch_json(session, f"{algolia_base}/items/{story_id}")
        if not isinstance(data, dict):
            return []

        children = data.get("children", [])
        comments = []
        for child in children[:comment_limit]:
            if child.get("author") and child.get("text"):
                # Skip deleted/dead comments
                if child.get("deleted") or child.get("dead"):
                    continue
                comments.append({
                    "comment_id": str(child.get("id", "")),
                    "story_id": str(story_id),
                    "author": child.get("author", ""),
                    "body_text": child.get("text", "")[:10000],
                    "score": child.get("points", 0),
                    "parent_id": str(child.get("parent_id", "")),
                    "story_title": story_title[:1000],
                })
        return comments

    def _insert_story(self, cursor, story: dict, result: CollectionResult) -> None:
        """Insert a story into social_posts and raw_signals."""
        title = story.get("title", "")
        url = story.get("url", "")
        story_text = title + " " + (story.get("text", "") or "")
        entity_name, entity_type = self._extract_entity(story_text)

        points = story.get("score", 0)
        descendants = story.get("descendants", 0)
        raw_score = self._compute_score(points, descendants)

        published_at = None
        if story.get("time"):
            try:
                published_at = datetime.fromtimestamp(story["time"], tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                pass

        # Dual-write: social_posts (shared table)
        cursor.execute(
            """INSERT INTO social_posts
               (platform, post_id, title, body_text, author, score, num_comments,
                url, subreddit, entity_name, entity_type, published_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 score = VALUES(score),
                 num_comments = VALUES(num_comments)""",
            (
                "hn_live",
                str(story.get("id", "")),
                title[:1000],
                (story.get("text", "") or "")[:5000],
                story.get("by", ""),
                points,
                descendants,
                url,
                "hacker_news",
                entity_name,
                entity_type,
                published_at,
            ),
        )

        # Dual-write: raw_signals (for scoring pipeline)
        cursor.execute(
            """INSERT IGNORE INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at, collected_at, processed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
            (
                "hn_live",
                "hn_live",
                url or f"https://news.ycombinator.com/item?id={story.get('id', '')}",
                title[:1000],
                (story.get("text", "") or "")[:5000],
                entity_name,
                published_at,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "hn_live",
            title=title[:1000],
            entity_name=entity_name,
            source_url=url or f"https://news.ycombinator.com/item?id={story.get('id', '')}",
            body_text=(story.get("text", "") or "")[:5000],
            raw_score=raw_score,
            points=points,
            num_comments=descendants,
            platform="hacker_news",
        )

        result.records_collected += 1

    def _insert_comments(self, cursor, comments: list[dict],
                         result: CollectionResult) -> None:
        """Insert comments into hn_live_comments table."""
        for comment in comments:
            try:
                cursor.execute(
                    """INSERT INTO hn_live_comments
                       (comment_id, story_id, author, body_text, score,
                        parent_id, story_title, collected_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE score = VALUES(score)""",
                    (
                        comment["comment_id"],
                        comment["story_id"],
                        comment["author"],
                        comment["body_text"],
                        comment["score"],
                        comment["parent_id"],
                        comment["story_title"],
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                result.records_collected += 1
            except Exception as e:
                result.errors.append(f"Error inserting HN comment {comment.get('comment_id', '?')}: {e}")

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("hn_live", {})

        if self.dry_run:
            result.status = "success"
            return result

        session = get_http_session(timeout=20)
        firebase_base = config.get("firebase", {}).get(
            "base_url", _FIREBASE_BASE,
        )
        algolia_base = config.get("algolia", {}).get(
            "base_url", _ALGOLIA_BASE,
        )
        max_stories = config.get("max_stories", 50)
        min_points = config.get("min_points", 5)
        comment_limit = config.get("comment_limit", 5)
        collect_comments = config.get("collect_comments", True)

        cursor = conn.cursor()

        # Ensure comments table exists
        cursor.execute(_CREATE_TABLE_SQL)

        # Fetch new story IDs from Firebase
        story_ids = self._fetch_new_story_ids(session, firebase_base)
        if not story_ids:
            _logger.info("HNLiveCollector: no new stories found")
            result.status = "partial"
            cursor.close()
            conn.commit()
            return result

        # Process stories (limited by max_stories)
        stories_to_comment = []  # High-engagement stories for comment fetching
        processed = 0

        for story_id in story_ids[:max_stories]:
            story = self._fetch_story(session, firebase_base, story_id)
            if not isinstance(story, dict):
                continue

            # Skip non-story items (comments, polls, jobs if not relevant)
            if story.get("type") != "story":
                continue

            try:
                self._insert_story(cursor, story, result)

                # Track high-engagement stories for comment collection
                if (collect_comments and
                        story.get("score", 0) >= min_points and
                        story.get("descendants", 0) > 0):
                    stories_to_comment.append(story)

                processed += 1
            except Exception as e:
                result.errors.append(f"Error processing story {story_id}: {e}")

        # Phase 2: Fetch comments from high-engagement stories via Algolia
        for story in stories_to_comment:
            try:
                comments = self._fetch_comments(
                    session, algolia_base,
                    story.get("id", 0),
                    story.get("title", ""),
                    comment_limit,
                )
                self._insert_comments(cursor, comments, result)
            except Exception as e:
                result.errors.append(
                    f"Error fetching comments for story {story.get('id', '?')}: {e}"
                )

        _logger.info(
            "HNLiveCollector: %d stories processed, %d queued for comments",
            processed, len(stories_to_comment),
        )

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
