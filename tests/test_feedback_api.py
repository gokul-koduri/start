"""Tests for the feedback API endpoints (api/v2/feedback.py)."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFeedbackImport(unittest.TestCase):
    """Test feedback module can be imported."""

    def test_import_feedback_router(self):
        from api.v2.feedback import (
            router,
            submit_score_feedback,
            submit_feature_request,
        )

        self.assertIsNotNone(router)
        self.assertTrue(callable(submit_score_feedback))
        self.assertTrue(callable(submit_feature_request))

    def test_router_has_feedback_prefix(self):
        from api.v2.feedback import router

        self.assertEqual(router.prefix, "/v2/feedback")


class TestScoreFeedback(unittest.TestCase):
    """Test /v2/feedback/score endpoint."""

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    def test_submit_score_success(self, mock_schema, mock_conn):
        """Test successful score feedback submission."""
        from api.v2.feedback import submit_score_feedback

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"composite_score": 72.5}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_connection

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = submit_score_feedback(
            mock_request,
            {"entity_name": "Fisker", "rating": 4, "comment": "Accurate"},
        )

        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["entity_name"], "Fisker")
        mock_cursor.execute.assert_called()

    def test_submit_score_missing_entity(self):
        """Test that missing entity_name returns 400."""
        from fastapi import HTTPException
        from api.v2.feedback import submit_score_feedback

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with self.assertRaises(HTTPException) as ctx:
            submit_score_feedback(
                mock_request,
                {"entity_name": "", "rating": 4},
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_submit_score_invalid_rating(self):
        """Test that invalid rating returns 400."""
        from fastapi import HTTPException
        from api.v2.feedback import submit_score_feedback

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with self.assertRaises(HTTPException) as ctx:
            submit_score_feedback(
                mock_request,
                {"entity_name": "TestCo", "rating": 6},
            )
        self.assertEqual(ctx.exception.status_code, 400)


class TestFeatureRequest(unittest.TestCase):
    """Test /v2/feedback/feature endpoint."""

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    def test_submit_new_feature(self, mock_schema, mock_conn):
        """Test submitting a new feature request."""
        from api.v2.feedback import submit_feature_request

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No existing feature
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_connection

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = submit_feature_request(
            mock_request,
            {"feature": "Add Slack integration for alerts", "category": "integrations"},
        )

        self.assertEqual(result["status"], "created")

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    def test_upvote_existing_feature(self, mock_schema, mock_conn):
        """Test upvoting an existing feature request."""
        from api.v2.feedback import submit_feature_request

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 5, "upvotes": 3}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_connection

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = submit_feature_request(
            mock_request,
            {"feature": "Add Slack integration for alerts"},
        )

        self.assertEqual(result["status"], "upvoted")
        self.assertEqual(result["upvotes"], 4)

    def test_submit_feature_too_short(self):
        """Test that feature request under 5 chars returns 400."""
        from fastapi import HTTPException
        from api.v2.feedback import submit_feature_request

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with self.assertRaises(HTTPException) as ctx:
            submit_feature_request(
                mock_request,
                {"feature": "Hi"},
            )
        self.assertEqual(ctx.exception.status_code, 400)


class TestIpHashing(unittest.TestCase):
    """Test privacy-preserving IP hashing."""

    def test_hash_ip_returns_consistent_hash(self):
        from api.v2.feedback import _hash_ip

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"

        hash1 = _hash_ip(mock_request)
        hash2 = _hash_ip(mock_request)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)

    def test_hash_ip_different_for_different_ips(self):
        from api.v2.feedback import _hash_ip

        mock_req1 = MagicMock()
        mock_req1.client.host = "192.168.1.1"
        mock_req2 = MagicMock()
        mock_req2.client.host = "10.0.0.1"

        self.assertNotEqual(_hash_ip(mock_req1), _hash_ip(mock_req2))


if __name__ == "__main__":
    unittest.main()
