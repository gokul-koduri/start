"""Tests for the Product Hunt Collector."""

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

from collectors.producthunt_collector import ProductHuntCollector  # noqa: E402
from collectors.base import CollectionResult  # noqa: E402

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_post(
    ph_id="ph-123",
    name="AI Writer Pro",
    tagline="AI-powered writing assistant",
    votes_count=300,
    comments_count=45,
    topics=None,
    makers=None,
    featured=False,
    created_at=None,
):
    """Build a post dict matching _parse_post output."""
    now = datetime.now(timezone.utc)
    return {
        "ph_id": ph_id,
        "name": name,
        "tagline": tagline,
        "description": f"Description for {name}",
        "product_url": f"https://producthunt.com/posts/{ph_id}",
        "votes_count": votes_count,
        "comments_count": comments_count,
        "topics": topics or ["ai", "saas"],
        "makers": makers or ["Alice Smith", "Bob Jones"],
        "website_url": f"https://{name.lower().replace(' ', '')}.com",
        "featured": featured,
        "created_at": created_at
        or (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
        "featured_at": (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
        if featured
        else None,
    }


def _make_graphql_response(posts=None, has_next_page=False, end_cursor="cursor123"):
    """Build a valid Product Hunt GraphQL response envelope."""
    edges = []
    for p in posts or []:
        topics_edges = [{"node": {"name": t}} for t in p.get("topics", [])]
        maker_edges = [
            {"node": {"id": f"m{i}", "name": m, "username": m.lower().replace(" ", "")}}
            for i, m in enumerate(p.get("makers", []))
        ]
        edges.append(
            {
                "node": {
                    "id": p["ph_id"],
                    "name": p["name"],
                    "tagline": p["tagline"],
                    "description": p["description"],
                    "url": p["product_url"],
                    "votesCount": p["votes_count"],
                    "commentsCount": p["comments_count"],
                    "createdAt": p["created_at"],
                    "featuredAt": p.get("featured_at"),
                    "topics": {"edges": topics_edges},
                    "website": {"url": p["website_url"]},
                    "makers": {"edges": maker_edges},
                }
            }
        )

    return {
        "data": {
            "posts": {
                "edges": edges,
                "pageInfo": {
                    "hasNextPage": has_next_page,
                    "endCursor": end_cursor if has_next_page else None,
                },
            }
        }
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning JSON dicts in order."""
    session = MagicMock()
    session.headers = {}
    response_list = list(responses or [])

    def mock_post(url, json=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        if response_list:
            resp.json.return_value = response_list.pop(0)
        else:
            resp.json.return_value = {}
        return resp

    session.post = mock_post
    return session


class TestProductHuntCollectorName:
    def test_name(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        assert c.name == "producthunt"


class TestProductHuntCollectorConfig:
    def test_dry_run_mode(self):
        c = ProductHuntCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0

    def test_no_api_token(self):
        c = ProductHuntCollector(config={"producthunt": {}})
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "failed"
        assert any("API token" in e for e in result.errors)


class TestProductHuntCollectorScoring:
    def test_high_engagement_featured(self):
        c = ProductHuntCollector(config={})
        post = _make_post(
            votes_count=600,
            comments_count=80,
            featured=True,
            topics=["ai", "saas"],
            created_at=(datetime.now(timezone.utc) - timedelta(hours=6)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
        score = c._compute_score(post)
        # >500 votes(+35) + high comments(+15) + featured(+15) + relevant topic(+15) + <24h(+20) = 100
        assert score >= 90

    def test_low_engagement(self):
        c = ProductHuntCollector(config={})
        post = _make_post(
            votes_count=5,
            comments_count=0,
            featured=False,
            topics=["design"],
            created_at=(datetime.now(timezone.utc) - timedelta(days=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
        score = c._compute_score(post)
        assert score < 20

    def test_medium_engagement(self):
        c = ProductHuntCollector(config={})
        post = _make_post(
            votes_count=200,
            comments_count=30,
            featured=False,
            topics=["ai"],
            created_at=(datetime.now(timezone.utc) - timedelta(hours=36)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
        score = c._compute_score(post)
        # >100 votes(+20) + comments ratio(+15) + topic(+15) + <72h(+10) = 60
        assert score == 60

    def test_capped_at_100(self):
        c = ProductHuntCollector(config={})
        post = _make_post(
            votes_count=9999,
            comments_count=9999,
            featured=True,
            topics=["ai", "developer-tools"],
            created_at=(datetime.now(timezone.utc) - timedelta(hours=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
        score = c._compute_score(post)
        assert score <= 100.0

    def test_no_date(self):
        c = ProductHuntCollector(config={})
        post = _make_post(votes_count=600, featured=True, topics=["ai"])
        post["created_at"] = None  # Override default to actually test None
        score = c._compute_score(post)
        # >500 votes(+35) + featured(+15) + topic(+15) = 65 (no recency)
        assert score == 65


class TestProductHuntCollectorParse:
    def test_parse_valid_post(self):
        c = ProductHuntCollector(config={})
        graphql_resp = _make_graphql_response([_make_post()])
        node = graphql_resp["data"]["posts"]["edges"][0]["node"]
        post = c._parse_post(node)
        assert post is not None
        assert post["ph_id"] == "ph-123"
        assert post["name"] == "AI Writer Pro"
        assert post["votes_count"] == 300
        assert len(post["topics"]) == 2

    def test_parse_missing_fields(self):
        c = ProductHuntCollector(config={})
        node = {"id": "ph-999", "name": "Minimal"}
        post = c._parse_post(node)
        assert post is not None
        assert post["ph_id"] == "ph-999"
        assert post["votes_count"] == 0
        assert post["topics"] == []
        assert post["makers"] == []

    def test_parse_no_id(self):
        c = ProductHuntCollector(config={})
        node = {"name": "No ID"}
        post = c._parse_post(node)
        assert post is None


class TestProductHuntCollectorFetch:
    def test_fetch_posts_success(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        posts = [_make_post(), _make_post(ph_id="ph-456", name="Second Product")]
        resp = _make_graphql_response(posts)
        session = _make_mock_session([resp])
        result_posts, cursor = c._fetch_posts(session, "https://api.example.com", 50)
        assert len(result_posts) == 2
        assert result_posts[0]["ph_id"] == "ph-123"

    def test_fetch_empty(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        resp = _make_graphql_response([])
        session = _make_mock_session([resp])
        result_posts, cursor = c._fetch_posts(session, "https://api.example.com", 50)
        assert len(result_posts) == 0

    def test_fetch_pagination(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        resp = _make_graphql_response(
            [_make_post()], has_next_page=True, end_cursor="next123"
        )
        session = _make_mock_session([resp])
        result_posts, cursor = c._fetch_posts(session, "https://api.example.com", 50)
        assert len(result_posts) == 1
        assert cursor == "next123"

    def test_fetch_api_failure(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        session = MagicMock()
        session.post.side_effect = Exception("Connection refused")
        result_posts, cursor = c._fetch_posts(session, "https://api.example.com", 50)
        assert len(result_posts) == 0
        assert cursor is None


class TestProductHuntCollectorInsert:
    def test_insert_single_post(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="producthunt")

        post = _make_post()
        c._insert_post(mock_cursor, post, result)
        assert result.records_collected == 1
        # 2 SQL calls: producthunt_launches + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_posts(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="producthunt")

        for i in range(5):
            c._insert_post(mock_cursor, _make_post(ph_id=f"ph-{i}"), result)
        assert result.records_collected == 5

    def test_insert_post_no_makers(self):
        c = ProductHuntCollector(config={"producthunt": {"api_token": "test"}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="producthunt")

        post = _make_post(makers=[])
        c._insert_post(mock_cursor, post, result)
        assert result.records_collected == 1


class TestProductHuntCollectorIntegration:
    @patch("collectors.producthunt_collector.time")
    @patch("collectors.producthunt_collector.get_http_session")
    def test_collect_full_flow(self, mock_get_session, mock_time):
        posts = [
            _make_post(ph_id="ph-1", name="Product One", topics=["ai"]),
            _make_post(ph_id="ph-2", name="Product Two", topics=["developer-tools"]),
        ]
        resp = _make_graphql_response(posts)
        session = _make_mock_session([resp])
        mock_get_session.return_value = session

        c = ProductHuntCollector(
            config={
                "producthunt": {
                    "api_token": "test",
                    "posts_per_request": 50,
                    "max_requests": 3,
                    "min_delay_seconds": 0,
                    "topic_filter": [],
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

    @patch("collectors.producthunt_collector.get_http_session")
    def test_collect_no_results(self, mock_get_session):
        resp = _make_graphql_response([])
        session = _make_mock_session([resp])
        mock_get_session.return_value = session

        c = ProductHuntCollector(
            config={
                "producthunt": {
                    "api_token": "test",
                    "max_requests": 1,
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

    @patch("collectors.producthunt_collector.get_http_session")
    def test_collect_with_topic_filter(self, mock_get_session):
        posts = [
            _make_post(ph_id="ph-1", topics=["ai"]),
            _make_post(ph_id="ph-2", topics=["gaming"]),
            _make_post(ph_id="ph-3", topics=["saas"]),
        ]
        resp = _make_graphql_response(posts)
        session = _make_mock_session([resp])
        mock_get_session.return_value = session

        c = ProductHuntCollector(
            config={
                "producthunt": {
                    "api_token": "test",
                    "max_requests": 1,
                    "min_delay_seconds": 0,
                    "topic_filter": ["ai", "saas"],
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 2  # Only "ai" and "saas" match

    @patch("collectors.producthunt_collector.get_http_session")
    def test_collect_handles_individual_error(self, mock_get_session):
        posts = [_make_post()]
        resp = _make_graphql_response(posts)
        session = _make_mock_session([resp])
        mock_get_session.return_value = session

        c = ProductHuntCollector(
            config={
                "producthunt": {
                    "api_token": "test",
                    "max_requests": 1,
                    "min_delay_seconds": 0,
                },
            }
        )

        call_count = {"n": 0}

        def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise Exception("DB error")

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = execute_side_effect

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert len(result.errors) > 0
