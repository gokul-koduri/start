"""Tests for the HN Live Collector."""

import json
import sys
from datetime import datetime, timezone
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

from collectors.hn_live_collector import HNLiveCollector, _CREATE_TABLE_SQL
from collectors.base import CollectionResult

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_story(sid=12345, title="Tech Corp launches AI platform",
               url="https://example.com", score=150, descendants=50,
               author="pg", time=1700000000, story_type="story", text=None):
    """Build a mock HN story object (Firebase API format)."""
    return {
        "id": sid,
        "title": title,
        "url": url,
        "score": score,
        "descendants": descendants,
        "by": author,
        "time": time,
        "type": story_type,
        "text": text or "",
    }


def _make_algolia_item(story_id=12345, title="Tech Corp launches AI platform",
                       points=150, children=None):
    """Build a mock Algolia item response with nested comments."""
    return {
        "id": str(story_id),
        "title": title,
        "points": points,
        "children": children or [
            {
                "id": "c1", "author": "user1", "text": "Great product!",
                "points": 25, "parent_id": story_id,
            },
            {
                "id": "c2", "author": "user2", "text": "This will change the industry.",
                "points": 18, "parent_id": story_id,
            },
        ],
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session that returns given JSON responses in order."""
    session = MagicMock()
    session.headers = {}
    response_iter = iter(responses or [])

    def mock_get(url, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        try:
            data = next(response_iter)
            resp.json.return_value = data
        except StopIteration:
            resp.json.return_value = {}
        return resp

    session.get = mock_get
    return session


class TestHNLiveCollectorName:
    def test_name(self):
        c = HNLiveCollector(config={"hn_live": {}})
        assert c.name == "hn_live"


class TestHNLiveCollectorConfig:
    def test_dry_run_mode(self):
        c = HNLiveCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0


class TestHNLiveCollectorScoring:
    def test_high_engagement(self):
        c = HNLiveCollector(config={})
        # 500 + (200*3) = 1100 / 10 = 100
        score = c._compute_score(points=500, num_comments=200)
        assert score > 80

    def test_low_engagement(self):
        c = HNLiveCollector(config={})
        score = c._compute_score(points=2, num_comments=0)
        assert score < 10

    def test_capped_at_100(self):
        c = HNLiveCollector(config={})
        score = c._compute_score(points=9999, num_comments=9999)
        assert score <= 100.0


class TestHNLiveCollectorEntityExtraction:
    def test_launch_entity(self):
        c = HNLiveCollector(config={})
        name, etype = c._extract_entity("Tech Corp releases new AI platform")
        assert etype == "company"
        assert name == "Tech Corp"

    def test_title_case_entity(self):
        c = HNLiveCollector(config={})
        name, etype = c._extract_entity("Stripe Connect updates pricing model")
        assert etype == "company"
        assert name == "Stripe Connect"

    def test_no_entity(self):
        c = HNLiveCollector(config={})
        name, _ = c._extract_entity("just some random text")
        assert name == ""


class TestHNLiveCollectorFetchStories:
    def test_fetch_new_stories(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_session = _make_mock_session([[1, 2, 3]])
        ids = c._fetch_new_story_ids(mock_session, "https://example.com/v0")
        assert ids == [1, 2, 3]

    def test_fetch_empty_stories(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_session = _make_mock_session([[]])
        ids = c._fetch_new_story_ids(mock_session, "https://example.com/v0")
        assert ids == []

    def test_fetch_story(self):
        c = HNLiveCollector(config={"hn_live": {}})
        story = _make_story(sid=42)
        mock_session = _make_mock_session([story])
        result = c._fetch_story(mock_session, "https://example.com/v0", 42)
        assert result is not None
        assert result["id"] == 42

    def test_api_failure(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection refused")
        result = c._fetch_new_story_ids(mock_session, "https://example.com/v0")
        assert result == []


class TestHNLiveCollectorInsertStories:
    def test_insert_single_story(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="hn_live")

        story = _make_story()
        c._insert_story(mock_cursor, story, result)
        assert result.records_collected == 1
        # 2 SQL calls: social_posts + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_stories(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="hn_live")

        for i in range(5):
            c._insert_story(mock_cursor, _make_story(sid=100 + i, title=f"Story {i}"), result)
        assert result.records_collected == 5

    def test_insert_story_no_url(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="hn_live")

        story = _make_story(url=None)
        c._insert_story(mock_cursor, story, result)
        assert result.records_collected == 1

    def test_insert_story_invalid_time(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="hn_live")

        story = _make_story(time=None)
        c._insert_story(mock_cursor, story, result)
        assert result.records_collected == 1


class TestHNLiveCollectorComments:
    def test_fetch_comments_enabled(self):
        c = HNLiveCollector(config={"hn_live": {}})
        algolia_item = _make_algolia_item(children=[
            {"id": "c1", "author": "u1", "text": "Nice!", "points": 10, "parent_id": 12345},
            {"id": "c2", "author": "u2", "text": "Agree.", "points": 5, "parent_id": 12345},
        ])
        mock_session = _make_mock_session([algolia_item])
        comments = c._fetch_comments(mock_session, "https://algolia.example.com", 12345, "Test", 5)
        assert len(comments) == 2
        assert comments[0]["comment_id"] == "c1"

    def test_fetch_comments_deleted(self):
        c = HNLiveCollector(config={"hn_live": {}})
        algolia_item = _make_algolia_item(children=[
            {"id": "c1", "author": "u1", "text": "Deleted", "points": 0,
             "parent_id": 12345, "deleted": True},
            {"id": "c2", "author": "u2", "text": "Dead", "points": 0,
             "parent_id": 12345, "dead": True},
            {"id": "c3", "author": "u3", "text": "Alive", "points": 5,
             "parent_id": 12345},
        ])
        mock_session = _make_mock_session([algolia_item])
        comments = c._fetch_comments(mock_session, "https://algolia.example.com", 12345, "Test", 5)
        assert len(comments) == 1
        assert comments[0]["comment_id"] == "c3"

    def test_fetch_comments_no_author(self):
        c = HNLiveCollector(config={"hn_live": {}})
        algolia_item = _make_algolia_item(children=[
            {"id": "c1", "text": "No author", "points": 5, "parent_id": 12345},
        ])
        mock_session = _make_mock_session([algolia_item])
        comments = c._fetch_comments(mock_session, "https://algolia.example.com", 12345, "Test", 5)
        assert len(comments) == 0  # Skipped because no author

    def test_insert_comments(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="hn_live")

        comments = [
            {"comment_id": "c1", "story_id": "123", "author": "u1",
             "body_text": "Great!", "score": 10, "parent_id": "123",
             "story_title": "Test"},
        ]
        c._insert_comments(mock_cursor, comments, result)
        assert result.records_collected == 1

    def test_insert_comments_error(self):
        c = HNLiveCollector(config={"hn_live": {}})
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        result = CollectionResult(collector_name="hn_live")

        comments = [
            {"comment_id": "c1", "story_id": "123", "author": "u1",
             "body_text": "Great!", "score": 10, "parent_id": "123",
             "story_title": "Test"},
        ]
        c._insert_comments(mock_cursor, comments, result)
        assert result.records_collected == 0
        assert len(result.errors) == 1


class TestHNLiveCollectorIntegration:
    @patch("collectors.hn_live_collector.get_http_session")
    def test_collect_full_flow(self, mock_get_session):
        """End-to-end test with mocked Firebase + Algolia."""
        # Responses in order:
        # 1. /newstories.json → [42, 43]
        # 2. /item/42.json → story1 (high engagement)
        # 3. /item/43.json → story2 (low engagement)
        # 4. Algolia /items/42 → comments for story1
        story1 = _make_story(sid=42, title="AI Startup raises $100M", score=200, descendants=80)
        story2 = _make_story(sid=43, title="Show HN: My side project", score=5, descendants=2)
        algolia_resp = _make_algolia_item(story_id=42, title="AI Startup raises $100M", children=[
            {"id": "c1", "author": "u1", "text": "Impressive!", "points": 50, "parent_id": 42},
        ])

        mock_session = _make_mock_session([[42, 43], story1, story2, algolia_resp])
        mock_get_session.return_value = mock_session

        c = HNLiveCollector(config={
            "hn_live": {
                "max_stories": 10,
                "min_points": 10,
                "collect_comments": True,
                "comment_limit": 5,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "success"
        # 2 stories + 1 comment = 3 records
        assert result.records_collected == 3
        mock_conn.commit.assert_called()

    @patch("collectors.hn_live_collector.get_http_session")
    def test_collect_skips_non_stories(self, mock_get_session):
        """Test that non-story items (polls, comments) are skipped."""
        story = _make_story(sid=42, story_type="story", score=100)
        poll = _make_story(sid=43, story_type="poll", score=50)

        mock_session = _make_mock_session([[42, 43], story, poll])
        mock_get_session.return_value = mock_session

        c = HNLiveCollector(config={
            "hn_live": {
                "max_stories": 10,
                "collect_comments": False,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 1  # Only the story, poll skipped

    @patch("collectors.hn_live_collector.get_http_session")
    def test_collect_no_stories(self, mock_get_session):
        """Test handling when /newstories.json returns empty list."""
        mock_session = _make_mock_session([[]])
        mock_get_session.return_value = mock_session

        c = HNLiveCollector(config={"hn_live": {}})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0

    @patch("collectors.hn_live_collector.get_http_session")
    def test_collect_comments_disabled(self, mock_get_session):
        """Test with comment collection disabled."""
        story = _make_story(sid=42, score=200, descendants=80)

        mock_session = _make_mock_session([[42], story])
        mock_get_session.return_value = mock_session

        c = HNLiveCollector(config={
            "hn_live": {
                "max_stories": 10,
                "collect_comments": False,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 1  # Story only, no comments


class TestCreateTableSQL:
    def test_table_sql_valid(self):
        assert "hn_live_comments" in _CREATE_TABLE_SQL
        assert "comment_id" in _CREATE_TABLE_SQL
        assert "story_id" in _CREATE_TABLE_SQL
        assert "body_text" in _CREATE_TABLE_SQL
        assert "UNIQUE KEY" in _CREATE_TABLE_SQL
