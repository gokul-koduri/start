"""Product Hunt collector — fetches recently launched products from Product Hunt API.

Data source: Product Hunt GraphQL API v2.
Auth: Bearer token via Authorization header.
Rate limit: ~200 requests/hour — uses polite delay between paginated requests.

This collector tracks new product launches, upvote counts, topics, and maker
profiles — key signals for detecting new market entrants and product trends.
"""

import json
import logging
import time
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_BASE_URL = "https://api.producthunt.com/v2/api/graphql"

_GRAPHQL_QUERY = """
query($cursor: String) {
  posts(order: VOTES, first: %d, after: $cursor) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        commentsCount
        createdAt
        featuredAt
        topics { edges { node { name } } }
        website { url }
        makers { edges { node { id name username } } }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

# Topics considered relevant for startup/tech signal detection
_RELEVANT_TOPICS = {
    "ai",
    "developer-tools",
    "saas",
    "no-code",
    "open-source",
    "tech",
    "artificial-intelligence",
    "machine-learning",
    "productivity",
    "startup",
}


class ProductHuntCollector(BaseCollector):
    """Collects product launches from Product Hunt GraphQL API.

    Fetches recent posts ordered by votes, with optional topic filtering.
    Supports cursor-based pagination.

    Config options:
        producthunt.api_token: Product Hunt API token (${PRODUCTHUNT_API_TOKEN})
        producthunt.base_url: GraphQL endpoint
        producthunt.posts_per_request: posts per page (default: 50)
        producthunt.min_delay_seconds: delay between requests (default: 5)
        producthunt.max_requests: max paginated requests (default: 5)
        producthunt.topic_filter: list of topic names to include (empty = all)
    """

    @property
    def name(self) -> str:
        return "producthunt"

    def _build_session(self, config: dict):
        """Build HTTP session with Bearer token auth."""
        session = get_http_session(timeout=30)
        token = config.get("api_token", "")
        if token:
            session.headers["Authorization"] = f"Bearer {token}"
        session.headers["Content-Type"] = "application/json"
        return session

    def _fetch_posts(
        self,
        session,
        base_url: str,
        posts_per_page: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Execute GraphQL query and parse response.

        Returns (posts, next_cursor). next_cursor is None if no more pages.
        """
        query = _GRAPHQL_QUERY % posts_per_page
        payload = {"query": query}
        if cursor:
            payload["variables"] = {"cursor": cursor}

        try:
            resp = session.post(base_url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.warning("Product Hunt API request failed: %s", e)
            return [], None

        # Check for GraphQL errors
        errors = data.get("errors")
        if errors:
            for err in errors:
                _logger.warning(
                    "Product Hunt GraphQL error: %s", err.get("message", err)
                )
            return [], None

        posts_data = data.get("data", {}).get("posts", {})
        edges = posts_data.get("edges", [])
        page_info = posts_data.get("pageInfo", {})

        posts = []
        for edge in edges:
            node = edge.get("node", {})
            post = self._parse_post(node)
            if post:
                posts.append(post)

        next_cursor = (
            page_info.get("endCursor") if page_info.get("hasNextPage") else None
        )

        return posts, next_cursor

    def _parse_post(self, node: dict) -> dict | None:
        """Extract post metadata from GraphQL response node."""
        ph_id = str(node.get("id", ""))
        name = node.get("name", "")
        if not ph_id or not name:
            return None

        # Topics
        topic_edges = node.get("topics", {}).get("edges", [])
        topics = [
            e["node"]["name"] for e in topic_edges if e.get("node", {}).get("name")
        ]

        # Makers
        maker_edges = node.get("makers", {}).get("edges", [])
        makers = [
            e["node"].get("name", "")
            for e in maker_edges
            if e.get("node", {}).get("name")
        ]

        # Dates
        created_at = node.get("createdAt")
        featured_at = node.get("featuredAt")

        # Website
        website_url = node.get("website", {}).get("url", "")

        return {
            "ph_id": ph_id,
            "name": name,
            "tagline": node.get("tagline", ""),
            "description": node.get("description", ""),
            "product_url": node.get("url", ""),
            "votes_count": int(node.get("votesCount", 0) or 0),
            "comments_count": int(node.get("commentsCount", 0) or 0),
            "topics": topics,
            "makers": makers,
            "website_url": website_url,
            "featured": bool(featured_at),
            "created_at": self._parse_iso_date(created_at),
            "featured_at": self._parse_iso_date(featured_at),
        }

    def _parse_iso_date(self, date_str: str | None) -> str | None:
        """Parse ISO date string to YYYY-MM-DD format."""
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None

    def _compute_score(self, post: dict) -> float:
        """Compute signal strength (0-100).

        Factors:
          - High engagement (>500 upvotes): +35
          - Medium engagement (>100): +20
          - High comment ratio (comments > 10%% of votes): +15
          - Featured post: +15
          - Relevant topic: +15
          - Very recent (< 1 day): +20
          - Recent (< 3 days): +10
        """
        score = 0.0

        # Engagement
        votes = post.get("votes_count", 0)
        if votes > 500:
            score += 35
        elif votes > 100:
            score += 20
        elif votes > 20:
            score += 10

        # Comment ratio
        comments = post.get("comments_count", 0)
        if votes > 0 and comments > votes * 0.10:
            score += 15

        # Featured
        if post.get("featured"):
            score += 15

        # Topic relevance
        topics = set(t.lower() for t in post.get("topics", []))
        if topics & _RELEVANT_TOPICS:
            score += 15

        # Recency
        created_str = post.get("created_at")
        if created_str:
            try:
                created_dt = datetime.strptime(
                    created_str, "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                age_hours = (
                    datetime.now(timezone.utc) - created_dt
                ).total_seconds() / 3600
                if age_hours < 24:
                    score += 20
                elif age_hours < 72:
                    score += 10
            except (ValueError, TypeError):
                pass

        return min(score, 100.0)

    def _insert_post(self, cursor, post: dict, result: CollectionResult) -> None:
        """Insert post into producthunt_launches and raw_signals."""
        ph_id = post["ph_id"]
        name = post["name"]
        tagline = post["tagline"]
        description = post["description"]
        product_url = post["product_url"]
        votes_count = post["votes_count"]
        comments_count = post["comments_count"]
        topics = post["topics"]
        makers = post["makers"]
        website_url = post["website_url"]
        featured = post["featured"]
        created_at = post["created_at"]

        raw_score = self._compute_score(post)

        # Insert into producthunt_launches
        cursor.execute(
            """INSERT INTO producthunt_launches
               (ph_id, name, tagline, description, product_url, votes_count,
                comments_count, topics, makers, website_url, featured,
                launched_at, raw_score, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 votes_count = VALUES(votes_count),
                 comments_count = VALUES(comments_count),
                 raw_score = VALUES(raw_score),
                 collected_at = VALUES(collected_at)""",
            (
                ph_id,
                name,
                tagline or None,
                description or None,
                product_url,
                votes_count,
                comments_count,
                json.dumps(topics) if topics else None,
                json.dumps(makers) if makers else None,
                website_url or None,
                featured,
                created_at,
                raw_score,
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
                "producthunt",
                "producthunt",
                product_url,
                f"{name} — {tagline}" if tagline else name,
                description[:500] if description else "",
                makers[0] if makers else "",
                created_at,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "producthunt",
            title=name,
            entity_name=makers[0] if makers else "",
            source_url=product_url,
            body_text=tagline or "",
            raw_score=raw_score,
            votes_count=votes_count,
            comments_count=comments_count,
            topics=topics,
            featured=featured,
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("producthunt", {})

        if self.dry_run:
            result.status = "success"
            return result

        if not config.get("api_token"):
            _logger.warning("ProductHuntCollector: no API token configured")
            result.status = "failed"
            result.errors.append("No API token configured")
            return result

        base_url = config.get("base_url", _BASE_URL)
        posts_per_page = config.get("posts_per_request", 50)
        min_delay = config.get("min_delay_seconds", 5)
        max_requests = config.get("max_requests", 5)
        topic_filter = set(t.lower() for t in config.get("topic_filter", []))

        session = self._build_session(config)
        cursor = conn.cursor()

        page_cursor = None
        request_count = 0

        while request_count < max_requests:
            posts, next_cursor = self._fetch_posts(
                session, base_url, posts_per_page, page_cursor
            )

            if not posts:
                break

            for post in posts:
                # Apply topic filter if configured
                if topic_filter:
                    post_topics = set(t.lower() for t in post.get("topics", []))
                    if not (post_topics & topic_filter):
                        continue

                try:
                    self._insert_post(cursor, post, result)
                except Exception as e:
                    result.errors.append(
                        f"Error inserting post {post.get('ph_id', '?')}: {e}"
                    )

            request_count += 1

            if not next_cursor:
                break

            page_cursor = next_cursor
            time.sleep(min_delay)

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
