"""Reddit stream collector — real-time subreddit monitoring.

Extends the existing SocialMediaCollector (batch-based hot posts) by using
PRAW's stream API to capture new posts as they appear. Also collects top
comments from high-engagement posts for richer sentiment signals.

Complements the batch collector — both write to `social_posts` with
ON DUPLICATE KEY UPDATE for natural deduplication.

Data source: Reddit via PRAW (Python Reddit API Wrapper).
Rate limit: PRAW handles Reddit's rate limiting automatically.
"""

import logging
import re
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult

_logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reddit_stream_comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    comment_id VARCHAR(20) NOT NULL,
    post_id VARCHAR(20) NOT NULL,
    subreddit VARCHAR(100),
    author VARCHAR(200),
    body_text TEXT,
    score INT DEFAULT 0,
    permalink VARCHAR(500),
    published_at DATETIME,
    collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_comment (comment_id)
)
"""


class RedditStreamCollector(BaseCollector):
    """Collects Reddit posts in real-time via PRAW stream + top comments.

    Unlike SocialMediaCollector (batch hot posts), this collector:
      - Uses PRAW's stream API for near-real-time new post detection
      - Collects top comments from high-engagement posts
      - Focuses on startup/tech subreddits for opportunity signals
      - Writes comments to a dedicated reddit_stream_comments table

    Config options:
        reddit_client_id: Reddit OAuth client ID
        reddit_client_secret: Reddit OAuth client secret
        reddit_user_agent: Reddit API user agent string
        reddit_stream.subreddits: list of subreddit names to stream
        reddit_stream.stream_timeout: seconds to wait for new posts (default: 30)
        reddit_stream.max_posts: max posts to collect per run (default: 50)
        reddit_stream.min_score: minimum score for comment collection (default: 10)
        reddit_stream.comment_limit: top comments to fetch per post (default: 5)
        reddit_stream.collect_comments: whether to fetch comments (default: true)
    """

    @property
    def name(self) -> str:
        return "reddit_stream"

    def _init_praw(self):
        """Initialize PRAW Reddit instance."""
        try:
            import praw

            return praw.Reddit(
                client_id=self.config.get("reddit_client_id", ""),
                client_secret=self.config.get("reddit_client_secret", ""),
                user_agent=self.config.get(
                    "reddit_user_agent",
                    "OpportunityIntel/1.0 (research)",
                ),
            )
        except ImportError:
            _logger.warning("RedditStreamCollector: PRAW not installed")
            return None
        except Exception as e:
            _logger.warning("RedditStreamCollector: PRAW init failed: %s", e)
            return None

    def _extract_entity(self, text: str) -> tuple[str, str]:
        """Extract entity name and type from text using heuristics."""
        combined = text[:500]

        # Pattern: "$X raised ... CompanyName"
        match = re.search(
            r"\$(\d[\d,.]*)[MmBb]?\b.*?(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b)",
            combined,
        )
        if match:
            return match.group(2).strip(), "company"

        # Pattern: "Company launches/releases/announces"
        match = re.search(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b\s+(?:launches?|releases?|announces?|raises?|debuts?)",
            combined,
        )
        if match:
            return match.group(1).strip(), "company"

        # Title case phrase at start
        match = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", combined)
        if match and len(match.group(1)) < 40:
            return match.group(1).strip(), "company"

        return "", "company"

    def _compute_score(self, score: int, num_comments: int) -> float:
        """Compute engagement score (0-100)."""
        raw = score + (num_comments * 2)
        return min(raw / 10.0, 100.0)

    def _stream_posts(
        self, reddit, subreddits: list, config: dict, result: CollectionResult
    ) -> list:
        """Stream new posts from subreddits using PRAW stream API.

        Returns list of collected submission dicts for comment processing.
        """
        config.get("stream_timeout", 30)
        max_posts = config.get("max_posts", 50)
        posts_collected = []

        subreddit_names = "+".join(subreddits)
        multi = reddit.subreddit(subreddit_names)

        count = 0
        try:
            for submission in multi.stream.submissions(
                pause_after=0,  # Return None if no submissions available
                skip_existing=True,  # Only yield new submissions after start
            ):
                if submission is None:
                    # No new posts — check if we should keep waiting
                    if count >= max_posts:
                        break
                    continue

                post_data = {
                    "id": submission.id,
                    "title": submission.title,
                    "selftext": submission.selftext or "",
                    "author": str(submission.author)
                    if submission.author
                    else "[deleted]",
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "url": submission.url,
                    "permalink": submission.permalink,
                    "subreddit": str(submission.subreddit),
                    "created_utc": submission.created_utc,
                }
                posts_collected.append(post_data)
                count += 1

                if count >= max_posts:
                    break

        except Exception as e:
            result.errors.append(f"Reddit stream error: {e}")
            _logger.warning("RedditStreamCollector: stream error: %s", e)

        _logger.info(
            "RedditStreamCollector: streamed %d posts from r/%s",
            count,
            subreddit_names,
        )
        return posts_collected

    def _insert_posts(self, cursor, posts: list, result: CollectionResult) -> None:
        """Insert streamed posts into social_posts and raw_signals."""
        for post in posts:
            try:
                entity_name, entity_type = self._extract_entity(
                    post["title"] + " " + post["selftext"][:200],
                )

                raw_score = self._compute_score(
                    post["score"],
                    post["num_comments"],
                )

                published_at = None
                if post.get("created_utc"):
                    try:
                        published_at = datetime.fromtimestamp(
                            post["created_utc"],
                            tz=timezone.utc,
                        )
                    except (ValueError, TypeError, OSError):
                        pass

                # Insert into social_posts (shared table with batch collector)
                cursor.execute(
                    """INSERT INTO social_posts
                       (platform, post_id, title, body_text, author, score, num_comments,
                        url, subreddit, entity_name, entity_type, published_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                         score = VALUES(score),
                         num_comments = VALUES(num_comments)""",
                    (
                        "reddit_stream",
                        post["id"],
                        post["title"][:1000],
                        post["selftext"][:5000],
                        post["author"],
                        post["score"],
                        post["num_comments"],
                        post["url"],
                        post["subreddit"],
                        entity_name,
                        entity_type,
                        published_at,
                    ),
                )

                # Insert into raw_signals for scoring pipeline
                cursor.execute(
                    """INSERT IGNORE INTO raw_signals
                       (signal_type, source_name, source_url, title, body_text,
                        entity_name, published_at, collected_at, processed)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                    (
                        "reddit_stream",
                        "reddit_stream",
                        f"https://reddit.com{post['permalink']}",
                        post["title"][:1000],
                        post["selftext"][:5000],
                        entity_name,
                        published_at,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

                # Publish to Kafka for real-time stream processing
                self.publish_signal(
                    "reddit_stream",
                    title=post["title"][:1000],
                    entity_name=entity_name,
                    source_url=f"https://reddit.com{post['permalink']}",
                    body_text=post["selftext"][:5000],
                    raw_score=raw_score,
                    subreddit=post["subreddit"],
                    post_score=post["score"],
                    num_comments=post["num_comments"],
                )

                result.records_collected += 1

            except Exception as e:
                result.errors.append(f"Error inserting post {post.get('id', '?')}: {e}")

    def _collect_comments(
        self, reddit, posts: list, config: dict, cursor, result: CollectionResult
    ) -> None:
        """Fetch top comments from high-engagement posts."""
        if not config.get("collect_comments", True):
            return

        min_score = config.get("min_score", 10)
        comment_limit = config.get("comment_limit", 5)

        # Ensure comments table exists
        cursor.execute(_CREATE_TABLE_SQL)

        for post in posts:
            if post["score"] < min_score:
                continue

            try:
                submission = reddit.submission(id=post["id"])
                submission.comment_sort = "top"
                submission.comment_limit = comment_limit

                # Force load comments
                try:
                    submission.comments.replace_more(limit=0)
                except Exception:
                    pass

                for comment in submission.comments[:comment_limit]:
                    try:
                        comment_body = comment.body or ""
                        if not comment_body or comment_body == "[deleted]":
                            continue

                        published_at = None
                        if comment.created_utc:
                            try:
                                published_at = datetime.fromtimestamp(
                                    comment.created_utc,
                                    tz=timezone.utc,
                                )
                            except (ValueError, TypeError, OSError):
                                pass

                        cursor.execute(
                            """INSERT INTO reddit_stream_comments
                               (comment_id, post_id, subreddit, author, body_text,
                                score, permalink, published_at, collected_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                               ON DUPLICATE KEY UPDATE score = VALUES(score)""",
                            (
                                comment.id,
                                post["id"],
                                post["subreddit"],
                                str(comment.author) if comment.author else "[deleted]",
                                comment_body[:10000],
                                comment.score,
                                comment.permalink
                                if hasattr(comment, "permalink")
                                else "",
                                published_at,
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )
                        result.records_collected += 1

                    except Exception as e:
                        result.errors.append(
                            f"Error inserting comment {getattr(comment, 'id', '?')}: {e}",
                        )

            except Exception as e:
                result.errors.append(
                    f"Error fetching comments for post {post['id']}: {e}"
                )

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        stream_config = self.config.get("reddit_stream", {})

        if self.dry_run:
            result.status = "success"
            return result

        reddit = self._init_praw()
        if reddit is None:
            result.status = "failed"
            result.errors.append("PRAW not available")
            return result

        subreddits = stream_config.get(
            "subreddits",
            [
                "startups",
                "technology",
                "programming",
                "SaaS",
                "machinelearning",
                "artificial",
                "entrepreneur",
            ],
        )

        cursor = conn.cursor()

        # Phase 1: Stream new posts
        posts = self._stream_posts(reddit, subreddits, stream_config, result)
        self._insert_posts(cursor, posts, result)

        # Phase 2: Collect comments from high-engagement posts
        self._collect_comments(reddit, posts, stream_config, cursor, result)

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()

        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
