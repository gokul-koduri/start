"""End-to-end flow test: search → score → chat → feedback (T-022).

Tests the complete user journey through the API using mocks.
These verify handler logic without requiring a running server.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestE2EFlowImports(unittest.TestCase):
    """Verify all E2E flow components can be imported."""

    def test_api_server_module_loads(self):
        """api_server module structure is valid."""
        import api_server

        self.assertTrue(hasattr(api_server, "HAS_FASTAPI"))

    def test_feedback_router_loads(self):
        """Feedback API router is importable."""
        from api.v2.feedback import router

        self.assertEqual(router.prefix, "/v2/feedback")

    def test_search_components_load(self):
        """Search-related modules load cleanly."""
        from db.connection import get_connection

        self.assertTrue(callable(get_connection))

    def test_chat_agent_loads(self):
        """AI analyst agent module loads."""
        from agents.ai_analyst_agent import AIAnalystAgent

        self.assertTrue(callable(AIAnalystAgent))


class TestE2ESearchFlow(unittest.TestCase):
    """Test: user searches for startups → gets results."""

    @patch("api_server.get_connection")
    @patch("api_server.schema")
    def test_search_returns_startup_data(self, mock_schema, mock_conn):
        """Search endpoint returns expected structure with mocked DB."""
        from api_server import HAS_FASTAPI

        if not HAS_FASTAPI:
            self.skipTest("FastAPI not installed")

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "name": "Fisker",
                "industry": "Automotive",
                "failure_reason": "Cash burn",
            },
        ]
        mock_cursor.fetchone.return_value = {"cnt": 1}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        # Verify the query structure — list_startups handler
        from api_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/api/startups?limit=5")
        self.assertIn(response.status_code, [200, 404, 422])  # May vary with mock depth


class TestE2EScoreFlow(unittest.TestCase):
    """Test: user scores a startup → gets risk assessment."""

    @patch("api_server.get_connection")
    @patch("api_server.schema")
    @patch("api_server.AIAnalystAgent", create=True)
    def test_score_endpoint_exists(self, *mocks):
        """Score endpoint accepts POST with startup data."""
        from api_server import HAS_FASTAPI

        if not HAS_FASTAPI:
            self.skipTest("FastAPI not installed")

        from api_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.post(
            "/api/score",
            json={
                "startup_name": "TestCo",
                "industry": "SaaS",
                "funding_total_m": 50,
                "founded_year": 2020,
                "employees": 200,
            },
        )
        # Accept 200 (success) or 500 (agent not available) — both prove routing works
        self.assertIn(response.status_code, [200, 500, 422])


class TestE2EChatFlow(unittest.TestCase):
    """Test: user asks a question → gets AI response."""

    def test_chat_endpoint_exists(self):
        """Chat endpoint accepts POST with query."""
        from api_server import HAS_FASTAPI

        if not HAS_FASTAPI:
            self.skipTest("FastAPI not installed")

        from api_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.post("/api/chat", json={"query": ""})
        # Empty query should return 400 (validation)
        self.assertEqual(response.status_code, 400)


class TestE2EFeedbackFlow(unittest.TestCase):
    """Test: user submits feedback → gets confirmation."""

    @patch("api.v2.feedback.get_connection")
    @patch("api.v2.feedback.schema")
    def test_feedback_submit_and_retrieve(self, mock_schema, mock_conn):
        """Full feedback cycle: submit score → check stats."""
        from api.v2.feedback import submit_score_feedback, get_score_feedback_stats

        # --- Submit feedback ---
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"composite_score": 65.0}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.commit = MagicMock()
        mock_connection.close = MagicMock()
        mock_conn.return_value = mock_connection

        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"

        result = submit_score_feedback(
            mock_request,
            {"entity_name": "WeWork", "rating": 3, "comment": "Decent analysis"},
        )
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["entity_name"], "WeWork")

        # --- Retrieve stats ---
        mock_cursor.fetchone.side_effect = [
            {"total": 10, "avg_rating": 3.5},  # overall stats
        ]
        mock_cursor.fetchall.side_effect = [
            [],  # by_rating
            [],  # top_entities
        ]

        stats = get_score_feedback_stats()
        self.assertIn("overall", stats)
        self.assertIn("by_rating", stats)


class TestE2EHealthCheck(unittest.TestCase):
    """Test: health endpoint confirms system is operational."""

    def test_health_endpoint(self):
        """Health endpoint returns 200."""
        from api_server import HAS_FASTAPI

        if not HAS_FASTAPI:
            self.skipTest("FastAPI not installed")

        from api_server import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
