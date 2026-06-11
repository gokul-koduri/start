"""Tests for the Reddit Stream Collector."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Mock DB dependencies before importing collector ──
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

# Save originals so we don't poison other test modules
_saved_db_modules = {
    key: sys.modules.pop(key, None)
    for key in ("db", "db.connection", "db.schema", "db.dedup")
}

mock_db = MagicMock()
sys.modules["db"] = mock_db
sys.modules["db.connection"] = mock_db
sys.modules["db.connection"].get_connection = MagicMock()
sys.modules["db.schema"] = MagicMock()
sys.modules["db.dedup"] = MagicMock()
sys.modules["db.dedup"].dedup_startup = MagicMock(return_value=False)

from collectors.reddit_stream_collector import RedditStreamCollector, _CREATE_TABLE_SQL  # noqa: E402
from collectors.base import CollectionResult  # noqa: E402

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_submission(
    sid="abc123",
    title="StartupAI raises $50M Series B",
    selftext="A new AI startup just raised funding",
    author="user1",
    score=150,
    num_comments=45,
    url="https://reddit.com/r/startups/comments/abc123",
    permalink="/r/startups/comments/abc123",
    subreddit="startups",
    created_utc=1700000000.0,
):
    """Build a mock PRAW Submission object."""
    sub = MagicMock()
    sub.id = sid
    sub.title = title
    sub.selftext = selftext
    sub.author = author
    sub.score = score
    sub.num_comments = num_comments
    sub.url = url
    sub.permalink = permalink
    sub.subreddit = subreddit
    sub.created_utc = created_utc
    return sub


def _make_comment(cid="c1", body="Great product!", author="commenter1", score=25):
    """Build a mock PRAW Comment object."""
    c = MagicMock()
    c.id = cid
    c.body = body
    c.author = author
    c.score = score
    c.permalink = f"/r/startups/comments/abc123/_/{cid}"
    c.created_utc = 1700000100.0
    return c


def _make_mock_praw(submissions=None, comments=None):
    """Build a mock praw.Reddit instance."""
    mock_reddit = MagicMock()

    mock_stream = MagicMock()
    if submissions:
        submission_iter = iter(list(submissions) + [None, None])
    else:
        submission_iter = iter([None, None])
    mock_stream.submissions.return_value = submission_iter
    mock_stream.submissions.__iter__ = lambda self: submission_iter

    mock_subreddit = MagicMock()
    mock_subreddit.stream = mock_stream
    mock_reddit.subreddit = MagicMock(return_value=mock_subreddit)

    if comments is not None:
        mock_submission_obj = MagicMock()
        mock_submission_obj.comments = comments
        mock_submission_obj.comment_sort = None
        mock_submission_obj.comment_limit = None
        mock_reddit.submission.return_value = mock_submission_obj

    return mock_reddit


class TestRedditStreamCollectorName:
    def test_name(self):
        c = RedditStreamCollector(config={"reddit_stream": {}})
        assert c.name == "reddit_stream"


class TestRedditStreamCollectorConfig:
    def test_dry_run_mode(self):
        c = RedditStreamCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0

    def test_praw_not_available(self):
        c = RedditStreamCollector(config={"reddit_stream": {}})
        with patch(
            "collectors.reddit_stream_collector.RedditStreamCollector._init_praw",
            return_value=None,
        ):
            mock_conn = MagicMock()
            result = c.collect(mock_conn)
            assert result.status == "failed"
            assert any("PRAW" in e for e in result.errors)


class TestRedditStreamCollectorEntityExtraction:
    def test_extract_launch_entity(self):
        c = RedditStreamCollector(config={})
        # "Company launches" pattern requires 2+ title-case words before the verb
        name, etype = c._extract_entity("Tech Corp releases new model today")
        assert etype == "company"
        assert name == "Tech Corp"

    def test_extract_title_case_entity(self):
        c = RedditStreamCollector(config={})
        name, etype = c._extract_entity("Stripe Connect updates pricing")
        assert etype == "company"
        assert name == "Stripe Connect"

    def test_no_entity_found(self):
        c = RedditStreamCollector(config={})
        name, etype = c._extract_entity("just some random text")
        assert name == ""


class TestRedditStreamCollectorScoring:
    def test_high_engagement(self):
        c = RedditStreamCollector(config={})
        # 500 + (200*2) = 900 / 10 = 90
        score = c._compute_score(score=500, num_comments=200)
        assert score > 80

    def test_low_engagement(self):
        c = RedditStreamCollector(config={})
        score = c._compute_score(score=2, num_comments=0)
        assert score < 10

    def test_score_capped_at_100(self):
        c = RedditStreamCollector(config={})
        score = c._compute_score(score=9999, num_comments=9999)
        assert score <= 100.0


class TestRedditStreamCollectorInsertPosts:
    def test_insert_single_post(self):
        c = RedditStreamCollector(config={"reddit_stream": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="reddit_stream")

        posts = [
            {
                "id": "abc",
                "title": "Test Post",
                "selftext": "Body",
                "author": "user1",
                "score": 50,
                "num_comments": 10,
                "url": "https://example.com",
                "permalink": "/r/test/abc",
                "subreddit": "startups",
                "created_utc": 1700000000.0,
            }
        ]
        c._insert_posts(mock_cursor, posts, result)
        assert result.records_collected == 1
        # 2 SQL calls: social_posts + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_posts(self):
        c = RedditStreamCollector(config={"reddit_stream": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="reddit_stream")

        posts = [
            {
                "id": f"p{i}",
                "title": f"Post {i}",
                "selftext": "",
                "author": "u",
                "score": 10,
                "num_comments": 5,
                "url": "https://ex.com",
                "permalink": f"/r/t/{i}",
                "subreddit": "startups",
                "created_utc": 1700000000.0,
            }
            for i in range(5)
        ]
        c._insert_posts(mock_cursor, posts, result)
        assert result.records_collected == 5

    def test_insert_post_invalid_timestamp(self):
        c = RedditStreamCollector(config={"reddit_stream": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="reddit_stream")

        posts = [
            {
                "id": "bad",
                "title": "Bad Post",
                "selftext": "",
                "author": "u",
                "score": 10,
                "num_comments": 0,
                "url": "https://ex.com",
                "permalink": "/r/t/bad",
                "subreddit": "startups",
                "created_utc": None,
            }
        ]
        c._insert_posts(mock_cursor, posts, result)
        assert result.records_collected == 1

    def test_insert_post_error_captured(self):
        """Test that individual post errors are captured but don't stop processing."""
        c = RedditStreamCollector(config={"reddit_stream": {}})
        mock_cursor = MagicMock()
        # Make execute raise on first call (social_posts), succeed on second (raw_signals)
        mock_cursor.execute.side_effect = [Exception("DB error"), None]
        result = CollectionResult(collector_name="reddit_stream")

        posts = [
            {
                "id": "err",
                "title": "Error Post",
                "selftext": "",
                "author": "u",
                "score": 10,
                "num_comments": 0,
                "url": "https://ex.com",
                "permalink": "/r/t/err",
                "subreddit": "startups",
                "created_utc": 1700000000.0,
            }
        ]
        c._insert_posts(mock_cursor, posts, result)
        # Post processing errored, so count should still be 0
        assert result.records_collected == 0
        assert len(result.errors) == 1


class TestRedditStreamCollectorStream:
    def test_stream_posts_with_submissions(self):
        c = RedditStreamCollector(config={"reddit_stream": {"max_posts": 2}})
        mock_reddit = _make_mock_praw(
            submissions=[
                _make_submission(sid="s1"),
                _make_submission(sid="s2"),
            ]
        )
        result = CollectionResult(collector_name="reddit_stream")
        posts = c._stream_posts(mock_reddit, ["startups"], {"max_posts": 2}, result)
        assert len(posts) == 2
        assert posts[0]["id"] == "s1"

    def test_stream_no_new_posts(self):
        c = RedditStreamCollector(config={"reddit_stream": {}})
        mock_reddit = _make_mock_praw(submissions=[])
        result = CollectionResult(collector_name="reddit_stream")
        posts = c._stream_posts(mock_reddit, ["startups"], {}, result)
        assert len(posts) == 0

    def test_stream_stops_at_max(self):
        c = RedditStreamCollector(config={"reddit_stream": {"max_posts": 1}})
        mock_reddit = _make_mock_praw(
            submissions=[
                _make_submission(sid="s1"),
                _make_submission(sid="s2"),
                _make_submission(sid="s3"),
            ]
        )
        result = CollectionResult(collector_name="reddit_stream")
        posts = c._stream_posts(mock_reddit, ["startups"], {"max_posts": 1}, result)
        assert len(posts) == 1


class TestRedditStreamCollectorComments:
    def test_collect_comments_enabled(self):
        c = RedditStreamCollector(
            config={
                "reddit_stream": {
                    "collect_comments": True,
                    "min_score": 5,
                    "comment_limit": 3,
                },
            }
        )
        mock_reddit = MagicMock()
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="reddit_stream")

        posts = [{"id": "p1", "score": 100, "subreddit": "startups"}]

        # Use a real list as the mock comment forest — supports slicing natively
        comments_list = [_make_comment(cid=f"c{i}") for i in range(3)]

        class CommentList(list):
            """List subclass with replace_more() method for PRAW compatibility."""

            def replace_more(self, limit=0):
                pass

        mock_sub = MagicMock()
        mock_sub.comments = CommentList(comments_list)
        mock_reddit.submission.return_value = mock_sub

        c._collect_comments(
            mock_reddit,
            posts,
            {
                "collect_comments": True,
                "min_score": 5,
                "comment_limit": 3,
            },
            mock_cursor,
            result,
        )

        assert result.records_collected == 3
        assert mock_cursor.execute.call_count >= 1  # CREATE TABLE + inserts

    def test_collect_comments_disabled(self):
        c = RedditStreamCollector(
            config={
                "reddit_stream": {"collect_comments": False},
            }
        )
        mock_reddit = MagicMock()
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="reddit_stream")
        posts = [{"id": "p1", "score": 100, "subreddit": "startups"}]

        c._collect_comments(
            mock_reddit,
            posts,
            {
                "collect_comments": False,
            },
            mock_cursor,
            result,
        )

        assert result.records_collected == 0

    def test_collect_comments_below_min_score(self):
        c = RedditStreamCollector(
            config={
                "reddit_stream": {"collect_comments": True, "min_score": 50},
            }
        )
        mock_reddit = MagicMock()
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="reddit_stream")
        posts = [{"id": "p1", "score": 5, "subreddit": "startups"}]

        c._collect_comments(
            mock_reddit,
            posts,
            {
                "collect_comments": True,
                "min_score": 50,
                "comment_limit": 5,
            },
            mock_cursor,
            result,
        )

        assert result.records_collected == 0

    def test_collect_comments_skip_deleted(self):
        c = RedditStreamCollector(
            config={
                "reddit_stream": {"collect_comments": True, "min_score": 5},
            }
        )
        mock_reddit = MagicMock()
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="reddit_stream")
        posts = [{"id": "p1", "score": 100, "subreddit": "startups"}]

        class CommentList(list):
            def replace_more(self, limit=0):
                pass

        mock_sub = MagicMock()
        mock_sub.comments = CommentList([_make_comment(body="[deleted]")])
        mock_reddit.submission.return_value = mock_sub

        c._collect_comments(
            mock_reddit,
            posts,
            {
                "collect_comments": True,
                "min_score": 5,
                "comment_limit": 5,
            },
            mock_cursor,
            result,
        )

        assert result.records_collected == 0


class TestRedditStreamCollectorIntegration:
    @patch("collectors.reddit_stream_collector.RedditStreamCollector._init_praw")
    def test_collect_full_flow(self, mock_init_praw):
        """Test the full collect() flow with mocked PRAW."""
        mock_reddit = _make_mock_praw(
            submissions=[
                _make_submission(sid="s1", score=200),
                _make_submission(sid="s2", score=10),
            ]
        )
        mock_init_praw.return_value = mock_reddit

        c = RedditStreamCollector(
            config={
                "reddit_client_id": "test",
                "reddit_client_secret": "test",
                "reddit_stream": {
                    "subreddits": ["startups"],
                    "max_posts": 2,
                    "collect_comments": False,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 2
        mock_conn.commit.assert_called()


class TestCreateTableSQL:
    def test_table_sql_valid(self):
        assert "reddit_stream_comments" in _CREATE_TABLE_SQL
        assert "comment_id" in _CREATE_TABLE_SQL
        assert "post_id" in _CREATE_TABLE_SQL
        assert "body_text" in _CREATE_TABLE_SQL
        assert "UNIQUE KEY" in _CREATE_TABLE_SQL
