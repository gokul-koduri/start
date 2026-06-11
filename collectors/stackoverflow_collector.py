"""Stack Overflow collector — collects questions via the Stack Exchange API.

Data source: Stack Exchange API v2.3 (JSON, no auth required for basic access).
Rate limit: 300 requests/day on free tier; uses delay + backoff parameter.

Tracks technology adoption patterns, developer pain points, and emerging
tool trends from Stack Overflow questions matching configurable search terms.
Writes to stackoverflow_posts + raw_signals tables.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stackexchange.com/2.3"

# Tags relevant to startup/tech signal detection
_RELEVANT_TAGS = {
    "startup",
    "saas",
    "deployment",
    "kubernetes",
    "docker",
    "aws",
    "microservices",
    "machine-learning",
    "scaling",
    "architecture",
    "api-design",
    "devops",
    "serverless",
    "react",
    "node.js",
    "python",
    "tensorflow",
    "pytorch",
    "graphql",
    "terraform",
}

# Default search queries
_DEFAULT_QUERIES = [
    {
        "terms": "startup SaaS deployment",
        "tags": ["deployment", "saas"],
        "min_score": 5,
    },
    {
        "terms": "machine learning production",
        "tags": ["machine-learning", "production"],
        "min_score": 10,
    },
    {
        "terms": "scaling microservices architecture",
        "tags": ["microservices", "architecture"],
        "min_score": 5,
    },
]


class StackOverflowCollector(BaseCollector):
    """Collects Stack Overflow questions via the Stack Exchange API.

    Config options:
        stackoverflow.base_url: API base URL (default: https://api.stackexchange.com/2.3)
        stackoverflow.search_queries: list of {terms, tags, min_score} dicts
        stackoverflow.max_results_per_query: max items per request (default: 50)
        stackoverflow.min_delay_seconds: delay between requests (default: 2)
        stackoverflow.site: Stack Exchange site (default: stackoverflow)
        stackoverflow.timeout_seconds: HTTP timeout (default: 15)
    """

    @property
    def name(self) -> str:
        return "stackoverflow"

    def _strip_html(self, html_str: str) -> str:
        """Remove HTML tags from a string."""
        if not html_str:
            return ""
        return re.sub(r"<[^>]+>", " ", html_str).strip()

    def _fetch_questions(
        self, session, query: dict, max_results: int, site: str, timeout: int = 15
    ) -> list[dict]:
        """Fetch questions from Stack Exchange search API."""
        params = {
            "order": "desc",
            "sort": "activity",
            "site": site,
            "pagesize": min(max_results, 100),
            "filter": "withbody",
            "key": "none",
        }

        terms = query.get("terms", "")
        if terms:
            params["q"] = terms

        tags = query.get("tags", [])
        if tags:
            params["tagged"] = ";".join(tags)

        min_score = query.get("min_score", 0)
        if min_score > 0:
            params["min"] = min_score

        url = f"{self.config.get('stackoverflow', {}).get('base_url', _BASE_URL)}/search/advanced"

        try:
            resp = session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
        except Exception as e:
            _logger.warning("StackOverflowCollector: fetch failed — %s", e)
            return []

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            _logger.warning("StackOverflowCollector: JSON parse failed — %s", e)
            return []

        items = data.get("items", [])

        # Check rate limit
        quota = data.get("quota_remaining", -1)
        if 0 <= quota < 10:
            _logger.warning("StackOverflowCollector: low quota remaining (%d)", quota)

        posts = []
        for item in items:
            post = self._parse_item(item)
            if post:
                posts.append(post)

        return posts

    def _parse_item(self, item: dict) -> dict | None:
        """Extract question data from a Stack Exchange API item."""
        title = item.get("title", "").strip()
        if not title:
            return None

        # Extract owner info
        owner = item.get("owner", {})
        author_name = owner.get("display_name", "") if owner else ""
        author_reputation = owner.get("reputation", 0) if owner else 0

        # Parse creation date (Unix timestamp)
        created_at = None
        ts = item.get("creation_date")
        if ts:
            try:
                created_at = datetime.fromtimestamp(ts, tz=timezone.utc)
            except (TypeError, OSError):
                pass

        return {
            "post_id": item.get("question_id"),
            "title": title,
            "body_text": self._strip_html(item.get("body", ""))[:2000],
            "tags": item.get("tags", []),
            "score": item.get("score", 0),
            "answer_count": item.get("answer_count", 0),
            "view_count": item.get("view_count", 0),
            "author_name": author_name,
            "author_reputation": author_reputation,
            "is_answered": 1 if item.get("is_answered") else 0,
            "bounty_amount": item.get("bounty_amount", 0),
            "link": item.get("link", ""),
            "created_at": created_at,
        }

    def _compute_score(self, post: dict) -> float:
        """Compute signal strength (0-100).

        Factors:
          - Recency: <7d (+35), <30d (+20), <90d (+10)
          - Votes: >50 (+25), >20 (+15), >5 (+8)
          - Has bounty: +20
          - Has accepted answer: +10
          - Tag relevance: +10
          - Answer engagement (>5 answers): +10
          - Capped at 100
        """
        score = 0.0

        # Recency
        created = post.get("created_at")
        if created:
            age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            if age_hours < 168:  # 7 days
                score += 35
            elif age_hours < 720:  # 30 days
                score += 20
            elif age_hours < 2160:  # 90 days
                score += 10

        # Votes
        votes = post.get("score", 0)
        if votes > 50:
            score += 25
        elif votes > 20:
            score += 15
        elif votes > 5:
            score += 8

        # Bounty
        if post.get("bounty_amount", 0) > 0:
            score += 20

        # Accepted answer
        if post.get("is_answered"):
            score += 10

        # Tag relevance
        tags = post.get("tags", [])
        if any(t.lower() in _RELEVANT_TAGS for t in tags):
            score += 10

        # Answer engagement
        if post.get("answer_count", 0) > 5:
            score += 10

        return min(score, 100.0)

    def _insert_post(
        self,
        cursor,
        post: dict,
        search_term: str,
        raw_score: float,
        result: CollectionResult,
    ) -> None:
        """Insert question into stackoverflow_posts + raw_signals tables."""
        created_iso = None
        if post.get("created_at"):
            created_iso = post["created_at"].isoformat()

        # Insert into stackoverflow_posts
        cursor.execute(
            """INSERT IGNORE INTO stackoverflow_posts
               (post_id, title, body_text, tags, score, answer_count,
                view_count, author_name, author_reputation, is_answered,
                bounty_amount, link, created_at, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                post["post_id"],
                post["title"],
                post["body_text"][:2000],
                json.dumps(post["tags"]),
                post["score"],
                post["answer_count"],
                post["view_count"],
                post["author_name"],
                post["author_reputation"],
                post["is_answered"],
                post["bounty_amount"],
                post["link"],
                created_iso,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Insert into raw_signals
        ", ".join(post["tags"]) if post["tags"] else ""
        signal_title = f"[SO] {post['title']}"
        signal_body = post["body_text"][:500] if post["body_text"] else post["title"]

        cursor.execute(
            """INSERT IGNORE INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at, collected_at, processed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
            (
                "stackoverflow",
                "stackoverflow",
                post["link"],
                signal_title,
                signal_body,
                post["author_name"],
                created_iso,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "stackoverflow",
            title=signal_title,
            entity_name=post["author_name"],
            source_url=post["link"],
            body_text=signal_body[:300],
            raw_score=raw_score,
            signal_keywords=post["tags"],
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("stackoverflow", {})

        if self.dry_run:
            result.status = "success"
            return result

        search_queries = config.get("search_queries", _DEFAULT_QUERIES)
        max_results = config.get("max_results_per_query", 50)
        min_delay = config.get("min_delay_seconds", 2)
        site = config.get("site", "stackoverflow")
        timeout = config.get("timeout_seconds", 15)
        config.get("base_url", _BASE_URL)

        if not search_queries:
            _logger.info("StackOverflowCollector: no queries configured")
            result.status = "partial"
            return result

        session = get_http_session(timeout=timeout)
        session.headers["Accept"] = "application/json"

        cursor = conn.cursor()

        for query in search_queries:
            terms = query.get("terms", "")
            tags = query.get("tags", [])
            label = f"'{terms}' tags={tags}"

            posts = self._fetch_questions(session, query, max_results, site, timeout)
            _logger.info(
                "StackOverflowCollector: query %s → %d posts", label, len(posts)
            )

            for post in posts:
                raw_score = self._compute_score(post)

                try:
                    self._insert_post(cursor, post, terms, raw_score, result)
                except Exception as e:
                    result.errors.append(
                        f"Error inserting SO post {post.get('post_id')}: {e}"
                    )

            time.sleep(min_delay)

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
