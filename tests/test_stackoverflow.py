"""Tests for the Stack Overflow Collector."""

import json
import sys
from datetime import datetime, timezone, timedelta
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

from collectors.stackoverflow_collector import StackOverflowCollector  # noqa: E402
from collectors.base import CollectionResult  # noqa: E402

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_so_item(
    question_id=78901234,
    title="How to deploy ML model on Kubernetes?",
    body="<p>I'm trying to deploy...</p>",
    score=42,
    answer_count=5,
    view_count=3200,
    tags=None,
    author="devuser",
    reputation=1500,
    is_answered=True,
    bounty_amount=0,
    link="https://stackoverflow.com/questions/78901234",
    creation_date=None,
):
    """Build a mock Stack Exchange API item."""
    if tags is None:
        tags = ["kubernetes", "machine-learning", "docker"]
    if creation_date is None:
        creation_date = int(
            (datetime.now(timezone.utc) - timedelta(hours=12)).timestamp()
        )
    return {
        "question_id": question_id,
        "title": title,
        "body": body,
        "link": link,
        "score": score,
        "answer_count": answer_count,
        "view_count": view_count,
        "tags": tags,
        "owner": {"display_name": author, "reputation": reputation},
        "creation_date": creation_date,
        "is_answered": is_answered,
        "bounty_amount": bounty_amount,
    }


def _make_api_response(items=None, quota_remaining=298):
    """Build a mock Stack Exchange API JSON response."""
    return json.dumps(
        {
            "items": items or [],
            "has_more": False,
            "quota_remaining": quota_remaining,
        }
    )


def _make_so_post(
    title="How to deploy ML model on Kubernetes?",
    post_id=78901234,
    score=42,
    answer_count=5,
    tags=None,
    is_answered=True,
    bounty_amount=0,
    created_at=None,
    author_name="devuser",
    link="https://stackoverflow.com/questions/78901234",
):
    """Build a parsed post dict matching _parse_item output."""
    if tags is None:
        tags = ["kubernetes", "machine-learning", "docker"]
    if created_at is None:
        created_at = datetime.now(timezone.utc) - timedelta(hours=12)
    return {
        "post_id": post_id,
        "title": title,
        "body_text": "I'm trying to deploy...",
        "tags": tags,
        "score": score,
        "answer_count": answer_count,
        "view_count": 3200,
        "author_name": author_name,
        "author_reputation": 1500,
        "is_answered": 1 if is_answered else 0,
        "bounty_amount": bounty_amount,
        "link": link,
        "created_at": created_at,
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning JSON strings in order."""
    session = MagicMock()
    session.headers = {}
    rl = list(responses or [])

    def mock_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        if rl:
            data = rl.pop(0)
            resp.content = data.encode("utf-8") if isinstance(data, str) else data
            resp.json.return_value = json.loads(data) if isinstance(data, str) else {}
        else:
            resp.content = b""
            resp.json.return_value = {}
        return resp

    session.get = mock_get
    return session


class TestStackOverflowCollectorName:
    def test_name(self):
        c = StackOverflowCollector(config={})
        assert c.name == "stackoverflow"


class TestStackOverflowCollectorConfig:
    def test_dry_run_mode(self):
        c = StackOverflowCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0

    def test_no_queries(self):
        c = StackOverflowCollector(config={"stackoverflow": {"search_queries": []}})
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0


class TestStackOverflowCollectorScoring:
    def test_recent_high_votes(self):
        c = StackOverflowCollector(config={})
        post = _make_so_post(
            score=60,
            answer_count=6,
            created_at=datetime.now(timezone.utc) - timedelta(hours=6),
        )
        s = c._compute_score(post)
        # recency(<7d +35) + votes(>50 +25) + answered(+10) + tags(+10) + answers>5(+10) = 90
        assert s == 90.0

    def test_old_low_votes(self):
        c = StackOverflowCollector(config={})
        post = _make_so_post(
            score=2,
            is_answered=False,
            tags=["random", "unrelated"],
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
        )
        s = c._compute_score(post)
        assert s == 0.0

    def test_bounty_boost(self):
        c = StackOverflowCollector(config={})
        post = _make_so_post(
            bounty_amount=100,
            score=0,
            answer_count=0,
            is_answered=False,
            tags=["random"],
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
        )
        s = c._compute_score(post)
        # bounty(+20) = 20
        assert s == 20.0

    def test_accepted_answer(self):
        c = StackOverflowCollector(config={})
        post = _make_so_post(
            score=0,
            answer_count=0,
            tags=["random"],
            bounty_amount=0,
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
        )
        s = c._compute_score(post)
        # answered(+10) = 10
        assert s == 10.0

    def test_medium_votes(self):
        c = StackOverflowCollector(config={})
        post = _make_so_post(
            score=25,
            is_answered=False,
            tags=["random"],
            bounty_amount=0,
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
        )
        s = c._compute_score(post)
        # votes(>20 +15) = 15
        assert s == 15.0

    def test_capped_at_100(self):
        c = StackOverflowCollector(config={})
        post = _make_so_post(
            score=100,
            bounty_amount=200,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            tags=["saas", "kubernetes"],
        )
        s = c._compute_score(post)
        assert s <= 100.0


class TestStackOverflowCollectorParse:
    def test_parse_valid_item(self):
        c = StackOverflowCollector(config={})
        item = _make_so_item()
        post = c._parse_item(item)
        assert post is not None
        assert post["post_id"] == 78901234
        assert "deploy" in post["title"]
        assert post["score"] == 42
        assert "kubernetes" in post["tags"]

    def test_parse_no_title(self):
        c = StackOverflowCollector(config={})
        item = _make_so_item(title="")
        post = c._parse_item(item)
        assert post is None

    def test_parse_no_owner(self):
        c = StackOverflowCollector(config={})
        item = _make_so_item()
        del item["owner"]
        post = c._parse_item(item)
        assert post is not None
        assert post["author_name"] == ""
        assert post["author_reputation"] == 0


class TestStackOverflowCollectorStripHTML:
    def test_strip_paragraphs(self):
        c = StackOverflowCollector(config={})
        result = c._strip_html("<p>Hello world</p>")
        assert result == "Hello world"

    def test_strip_code(self):
        c = StackOverflowCollector(config={})
        result = c._strip_html("<code>import os</code>")
        assert result == "import os"

    def test_strip_complex_html(self):
        c = StackOverflowCollector(config={})
        html = '<p>Try using <code>docker run</code> with <a href="#">flags</a></p>'
        result = c._strip_html(html)
        assert "<" not in result
        assert "docker run" in result

    def test_strip_empty(self):
        c = StackOverflowCollector(config={})
        assert c._strip_html("") == ""
        assert c._strip_html(None) == ""


class TestStackOverflowCollectorFetch:
    def test_fetch_success(self):
        c = StackOverflowCollector(config={"stackoverflow": {}})
        item = _make_so_item()
        resp_json = _make_api_response([item])
        session = _make_mock_session([resp_json])
        posts = c._fetch_questions(session, {"terms": "test"}, 50, "stackoverflow")
        assert len(posts) == 1
        assert posts[0]["post_id"] == 78901234

    def test_fetch_empty(self):
        c = StackOverflowCollector(config={"stackoverflow": {}})
        resp_json = _make_api_response([])
        session = _make_mock_session([resp_json])
        posts = c._fetch_questions(session, {"terms": "test"}, 50, "stackoverflow")
        assert len(posts) == 0

    def test_fetch_api_failure(self):
        c = StackOverflowCollector(config={"stackoverflow": {}})
        session = MagicMock()
        session.get.side_effect = Exception("Connection refused")
        posts = c._fetch_questions(session, {"terms": "test"}, 50, "stackoverflow")
        assert len(posts) == 0

    def test_fetch_invalid_json(self):
        c = StackOverflowCollector(config={"stackoverflow": {}})
        session = _make_mock_session(["{not valid json}"])
        posts = c._fetch_questions(session, {"terms": "test"}, 50, "stackoverflow")
        assert len(posts) == 0


class TestStackOverflowCollectorInsert:
    def test_insert_single_post(self):
        c = StackOverflowCollector(config={"stackoverflow": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="stackoverflow")

        post = _make_so_post()
        c._insert_post(mock_cursor, post, "test query", 50, result)
        assert result.records_collected == 1
        # 2 SQL calls: stackoverflow_posts + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_posts(self):
        c = StackOverflowCollector(config={"stackoverflow": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="stackoverflow")

        for i in range(5):
            post = _make_so_post(post_id=1000 + i, title=f"Question {i}")
            c._insert_post(mock_cursor, post, "test", 0, result)
        assert result.records_collected == 5


class TestStackOverflowCollectorIntegration:
    @patch("collectors.stackoverflow_collector.time")
    @patch("collectors.stackoverflow_collector.get_http_session")
    def test_collect_full_flow(self, mock_get_session, mock_time):
        item = _make_so_item(title="How to scale SaaS app?")
        resp_json = _make_api_response([item])
        session = _make_mock_session([resp_json])
        mock_get_session.return_value = session

        c = StackOverflowCollector(
            config={
                "stackoverflow": {
                    "search_queries": [
                        {"terms": "SaaS scaling", "tags": ["saas"], "min_score": 5}
                    ],
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 1
        mock_conn.commit.assert_called()

    @patch("collectors.stackoverflow_collector.get_http_session")
    def test_collect_empty_results(self, mock_get_session):
        resp_json = _make_api_response([])
        session = _make_mock_session([resp_json])
        mock_get_session.return_value = session

        c = StackOverflowCollector(
            config={
                "stackoverflow": {
                    "search_queries": [
                        {"terms": "nonexistent", "tags": [], "min_score": 100}
                    ],
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0

    @patch("collectors.stackoverflow_collector.time")
    @patch("collectors.stackoverflow_collector.get_http_session")
    def test_collect_multiple_queries(self, mock_get_session, mock_time):
        item1 = _make_so_item(question_id=1, title="Q1")
        item2 = _make_so_item(question_id=2, title="Q2")
        session = _make_mock_session(
            [
                _make_api_response([item1]),
                _make_api_response([item2]),
            ]
        )
        mock_get_session.return_value = session

        c = StackOverflowCollector(
            config={
                "stackoverflow": {
                    "search_queries": [
                        {"terms": "query1", "tags": [], "min_score": 0},
                        {"terms": "query2", "tags": [], "min_score": 0},
                    ],
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 2

    @patch("collectors.stackoverflow_collector.time")
    @patch("collectors.stackoverflow_collector.get_http_session")
    def test_collect_handles_insert_error(self, mock_get_session, mock_time):
        item = _make_so_item()
        session = _make_mock_session([_make_api_response([item])])
        mock_get_session.return_value = session

        c = StackOverflowCollector(
            config={
                "stackoverflow": {
                    "search_queries": [{"terms": "test", "tags": [], "min_score": 0}],
                    "min_delay_seconds": 0,
                },
            }
        )

        call_count = {"n": 0}

        def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("DB error")

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = execute_side_effect

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert len(result.errors) > 0
