"""Tests for feedback API router (api/v2/feedback.py)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFeedbackRouterImport(unittest.TestCase):
    """Test that the feedback router module can be imported."""

    def test_import_feedback_module(self):
        """Feedback router module imports without error."""
        from api.v2.feedback import router

        self.assertIsNotNone(router)

    def test_router_has_routes(self):
        """Router has the expected 5 routes."""
        from api.v2.feedback import router

        routes = [r.path for r in router.routes]
        self.assertIn("/v2/feedback/score", routes)
        self.assertIn("/v2/feedback/feature", routes)
        self.assertIn("/v2/feedback/feature-requests", routes)
        self.assertIn("/v2/feedback/score-stats", routes)
        self.assertIn("/v2/feedback/dashboard", routes)

    def test_router_prefix(self):
        """Router has correct prefix."""
        from api.v2.feedback import router

        self.assertEqual(router.prefix, "/v2/feedback")


class TestHashIP(unittest.TestCase):
    """Test privacy-preserving IP hashing."""

    def test_hash_ip_basic(self):
        """_hash_ip returns a 16-char hex string."""
        from api.v2.feedback import _hash_ip

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        result = _hash_ip(mock_request)
        self.assertEqual(len(result), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))

    def test_hash_ip_consistent(self):
        """Same IP produces same hash."""
        from api.v2.feedback import _hash_ip

        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"
        h1 = _hash_ip(mock_request)
        h2 = _hash_ip(mock_request)
        self.assertEqual(h1, h2)

    def test_hash_ip_different_for_different_ips(self):
        """Different IPs produce different hashes."""
        from api.v2.feedback import _hash_ip

        r1 = MagicMock()
        r1.client.host = "10.0.0.1"
        r2 = MagicMock()
        r2.client.host = "10.0.0.2"
        self.assertNotEqual(_hash_ip(r1), _hash_ip(r2))


class TestFeedbackSchema(unittest.TestCase):
    """Test feedback table definitions in db/schema.py."""

    def test_schema_version_bumped(self):
        """Schema version is at least 17 (feedback tables added)."""
        from db.schema import get_schema_version

        self.assertGreaterEqual(get_schema_version(), 17)

    def test_feedback_tables_in_schema(self):
        """Feedback table SQL is present in _TABLES."""
        from db.schema import _TABLES

        table_sql = " ".join(_TABLES)
        self.assertIn("query_log", table_sql)
        self.assertIn("chat_log", table_sql)
        self.assertIn("score_feedback", table_sql)
        self.assertIn("feature_requests", table_sql)

    def test_query_log_has_required_columns(self):
        """query_log table has essential columns."""
        from db.schema import _TABLES

        " ".join(_TABLES)
        # Find the query_log table definition
        for t in _TABLES:
            if "query_log" in t:
                self.assertIn("query", t)
                self.assertIn("search_mode", t)
                self.assertIn("results_count", t)
                self.assertIn("ip_hash", t)
                break

    def test_score_feedback_has_rating(self):
        """score_feedback table has rating column."""
        from db.schema import _TABLES

        for t in _TABLES:
            if "score_feedback" in t:
                self.assertIn("rating", t)
                self.assertIn("entity_name", t)
                break

    def test_feature_requests_has_upvotes(self):
        """feature_requests table has upvotes and status."""
        from db.schema import _TABLES

        for t in _TABLES:
            if "feature_requests" in t:
                self.assertIn("upvotes", t)
                self.assertIn("status", t)
                break


class TestSubmitScoreFeedback(unittest.TestCase):
    """Test score feedback submission logic."""

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    @patch("api.v2.feedback._hash_ip", return_value="abc123")
    def test_submit_score_feedback_success(self, mock_hash, mock_schema, mock_conn):
        """Score feedback is inserted correctly."""
        from api.v2.feedback import submit_score_feedback

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"composite_score": 75.0}
        mock_conn.return_value.__enter__ = MagicMock(
            return_value=MagicMock(cursor=MagicMock(return_value=mock_cursor))
        )
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate context manager for connection
        conn_instance = MagicMock()
        cursor_cm = MagicMock()
        cursor_cm.__enter__ = MagicMock(return_value=mock_cursor)
        cursor_cm.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = cursor_cm
        mock_conn.return_value = conn_instance

        mock_request = MagicMock()
        body = {"entity_name": "Fisker", "rating": 4, "comment": "Accurate"}
        result = submit_score_feedback(mock_request, body)

        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["entity_name"], "Fisker")

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    def test_submit_score_feedback_missing_fields(self, mock_schema, mock_conn):
        """Missing fields returns 400 error."""
        from api.v2.feedback import submit_score_feedback
        from fastapi import HTTPException

        mock_request = MagicMock()
        with self.assertRaises(HTTPException) as ctx:
            submit_score_feedback(mock_request, {"entity_name": ""})
        self.assertEqual(ctx.exception.status_code, 400)


class TestSubmitFeatureRequest(unittest.TestCase):
    """Test feature request submission and upvoting."""

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    @patch("api.v2.feedback._hash_ip", return_value="abc123")
    def test_new_feature_request(self, mock_hash, mock_schema, mock_conn):
        """New feature request is created."""
        from api.v2.feedback import submit_feature_request

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No existing feature
        conn_instance = MagicMock()
        cursor_cm = MagicMock()
        cursor_cm.__enter__ = MagicMock(return_value=mock_cursor)
        cursor_cm.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = cursor_cm
        mock_conn.return_value = conn_instance

        mock_request = MagicMock()
        body = {"feature": "Add Slack alerts for score changes", "category": "alerts"}
        result = submit_feature_request(mock_request, body)
        self.assertEqual(result["status"], "created")

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    @patch("api.v2.feedback._hash_ip", return_value="abc123")
    def test_upvote_existing_feature(self, mock_hash, mock_schema, mock_conn):
        """Similar feature request gets upvoted."""
        from api.v2.feedback import submit_feature_request

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 42, "upvotes": 5}
        conn_instance = MagicMock()
        cursor_cm = MagicMock()
        cursor_cm.__enter__ = MagicMock(return_value=mock_cursor)
        cursor_cm.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = cursor_cm
        mock_conn.return_value = conn_instance

        mock_request = MagicMock()
        body = {"feature": "Slack alerts for score changes"}
        result = submit_feature_request(mock_request, body)
        self.assertEqual(result["status"], "upvoted")
        self.assertEqual(result["upvotes"], 6)

    @patch("api.v2.feedback._hash_ip", return_value="abc123")
    @patch("api.v2.feedback.schema")
    def test_feature_too_short(self, mock_schema, mock_hash):
        """Short feature description returns 400."""
        from api.v2.feedback import submit_feature_request
        from fastapi import HTTPException

        mock_request = MagicMock()
        with self.assertRaises(HTTPException) as ctx:
            submit_feature_request(mock_request, {"feature": "Hi"})
        self.assertEqual(ctx.exception.status_code, 400)


class TestFeedbackDashboard(unittest.TestCase):
    """Test the feedback dashboard endpoint."""

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    def test_dashboard_returns_all_sections(self, mock_schema, mock_conn):
        """Dashboard returns all expected sections."""
        from api.v2.feedback import get_feedback_dashboard

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = {"total": 0, "avg_rating": None}
        conn_instance = MagicMock()
        cursor_cm = MagicMock()
        cursor_cm.__enter__ = MagicMock(return_value=mock_cursor)
        cursor_cm.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = cursor_cm
        mock_conn.return_value = conn_instance

        result = get_feedback_dashboard()
        self.assertIn("top_queries", result)
        self.assertIn("recent_chats", result)
        self.assertIn("score_feedback", result)
        self.assertIn("top_feature_requests", result)
        self.assertIn("daily_query_counts", result)


class TestFeedbackScoreStats(unittest.TestCase):
    """Test the score stats aggregation endpoint."""

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    def test_score_stats_returns_overall(self, mock_schema, mock_conn):
        """Score stats returns overall summary."""
        from api.v2.feedback import get_score_feedback_stats

        mock_cursor = MagicMock()

        call_count = [0]

        def fetchall_side_effect():
            call_count[0] += 1
            if call_count[0] <= 1:
                return []
            elif call_count[0] <= 2:
                return ({"total": 0, "avg_rating": None},)
            return []

        mock_cursor.fetchall.side_effect = [
            [],  # by_rating
            {"total": 0, "avg_rating": None},  # overall
            [],  # top_entities
        ]
        mock_cursor.fetchone.return_value = {"total": 0, "avg_rating": None}

        conn_instance = MagicMock()
        cursor_cm = MagicMock()
        cursor_cm.__enter__ = MagicMock(return_value=mock_cursor)
        cursor_cm.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = cursor_cm
        mock_conn.return_value = conn_instance

        result = get_score_feedback_stats()
        self.assertIn("overall", result)


if __name__ == "__main__":
    unittest.main()
