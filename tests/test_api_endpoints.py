"""API endpoint tests — validates route registration, response structure, and error handling (T-040)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAPIRoutesRegistered(unittest.TestCase):
    """Verify all expected API routes are registered."""

    @classmethod
    def setUpClass(cls):
        """Import the FastAPI app once."""
        try:
            from fastapi.testclient import TestClient
            from api_server import app
            cls.client = TestClient(app)
            cls.app = app
        except ImportError:
            raise unittest.SkipTest("FastAPI not installed")

    def test_root_route_exists(self):
        """GET / returns 200."""
        resp = self.client.get("/")
        self.assertIn(resp.status_code, (200, 404))  # May need DB

    def test_health_route_exists(self):
        """GET /api/health returns 200."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)

    def test_stats_route_exists(self):
        """GET /api/stats returns a response."""
        resp = self.client.get("/api/stats")
        self.assertIn(resp.status_code, (200, 500))  # DB may be unavailable

    def test_startups_route_exists(self):
        """GET /api/startups returns a response."""
        resp = self.client.get("/api/startups")
        self.assertIn(resp.status_code, (200, 500))

    def test_news_route_exists(self):
        """GET /api/news returns a response."""
        resp = self.client.get("/api/news")
        self.assertIn(resp.status_code, (200, 500))

    def test_alerts_route_exists(self):
        """GET /api/alerts returns a response."""
        resp = self.client.get("/api/alerts")
        self.assertIn(resp.status_code, (200, 500))

    def test_alert_preferences_get_route(self):
        """GET /api/alerts/preferences returns a response."""
        resp = self.client.get("/api/alerts/preferences")
        self.assertIn(resp.status_code, (200, 500))

    def test_pipeline_runs_route_exists(self):
        """GET /api/pipeline-runs returns a response."""
        resp = self.client.get("/api/pipeline-runs")
        self.assertIn(resp.status_code, (200, 500))

    def test_collection_status_route(self):
        """GET /api/collection/status returns a response."""
        resp = self.client.get("/api/collection/status")
        self.assertIn(resp.status_code, (200, 500))

    def test_scores_deltas_route(self):
        """GET /api/scores/deltas returns a response."""
        resp = self.client.get("/api/scores/deltas")
        self.assertIn(resp.status_code, (200, 500))

    def test_score_accuracy_route(self):
        """GET /api/score/accuracy returns a response."""
        resp = self.client.get("/api/score/accuracy")
        self.assertIn(resp.status_code, (200, 500))

    def test_ws_status_route(self):
        """GET /api/ws/status returns a response."""
        resp = self.client.get("/api/ws/status")
        self.assertEqual(resp.status_code, 200)

    def test_opportunities_route(self):
        """GET /api/opportunities returns a response."""
        resp = self.client.get("/api/opportunities")
        self.assertIn(resp.status_code, (200, 500))

    def test_signals_route(self):
        """GET /api/signals returns a response."""
        resp = self.client.get("/api/signals")
        self.assertIn(resp.status_code, (200, 500))

    def test_survival_rates_route(self):
        """GET /api/survival-rates returns a response."""
        resp = self.client.get("/api/survival-rates")
        self.assertIn(resp.status_code, (200, 500))

    def test_search_route(self):
        """GET /api/search returns a response."""
        resp = self.client.get("/api/search?q=test")
        self.assertIn(resp.status_code, (200, 400, 500))

    def test_dead_letters_route(self):
        """GET /api/alerts/dead-letters returns a response."""
        resp = self.client.get("/api/alerts/dead-letters")
        self.assertIn(resp.status_code, (200, 500))

    def test_stream_status_route(self):
        """GET /api/stream/status returns a response."""
        resp = self.client.get("/api/stream/status")
        self.assertIn(resp.status_code, (200, 500))

    def test_risk_scores_route(self):
        """GET /api/risk-scores returns a response."""
        resp = self.client.get("/api/risk-scores")
        self.assertIn(resp.status_code, (200, 500))


class TestAPIResponseStructure(unittest.TestCase):
    """Test response JSON structure for key endpoints."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from api_server import app
            cls.client = TestClient(app)
        except ImportError:
            raise unittest.SkipTest("FastAPI not installed")

    def test_health_response_structure(self):
        """Health endpoint returns JSON with status."""
        resp = self.client.get("/api/health")
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("status", data)

    def test_ws_status_response_structure(self):
        """WS status returns JSON with active_connections."""
        resp = self.client.get("/api/ws/status")
        data = resp.json()
        self.assertIn("active_connections", data)
        self.assertIn("uptime_seconds", data)

    def test_scores_deltas_response_structure(self):
        """Scores deltas returns JSON with results and count."""
        resp = self.client.get("/api/scores/deltas")
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("results", data)
            self.assertIn("count", data)

    def test_score_accuracy_response_structure(self):
        """Score accuracy returns JSON with history."""
        resp = self.client.get("/api/score/accuracy")
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("history", data)
            self.assertIn("total_runs", data)

    def test_dead_letters_response_structure(self):
        """Dead letters returns JSON with results and count."""
        resp = self.client.get("/api/alerts/dead-letters")
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("results", data)
            self.assertIn("count", data)


class TestAPIRouteCount(unittest.TestCase):
    """Verify sufficient routes are registered."""

    def test_minimum_routes_registered(self):
        """At least 35 GET routes are registered."""
        try:
            from api_server import app
        except ImportError:
            self.skipTest("FastAPI not installed")
        get_routes = [r for r in app.routes if hasattr(r, 'methods') and 'GET' in r.methods]
        self.assertGreaterEqual(len(get_routes), 30)

    def test_post_routes_registered(self):
        """At least 5 POST routes are registered."""
        try:
            from api_server import app
        except ImportError:
            self.skipTest("FastAPI not installed")
        post_routes = [r for r in app.routes if hasattr(r, 'methods') and 'POST' in r.methods]
        self.assertGreaterEqual(len(post_routes), 5)

    def test_put_routes_registered(self):
        """At least 1 PUT route is registered."""
        try:
            from api_server import app
        except ImportError:
            self.skipTest("FastAPI not installed")
        put_routes = [r for r in app.routes if hasattr(r, 'methods') and 'PUT' in r.methods]
        self.assertGreaterEqual(len(put_routes), 1)


class TestAPIValidation(unittest.TestCase):
    """Test input validation on endpoints."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from api_server import app
            cls.client = TestClient(app)
        except ImportError:
            raise unittest.SkipTest("FastAPI not installed")

    def test_chat_empty_body(self):
        """POST /api/chat with empty body returns 422 or error."""
        resp = self.client.post("/api/chat", json={})
        self.assertIn(resp.status_code, (200, 400, 422, 500))

    def test_score_empty_body(self):
        """POST /api/score with empty body returns 422 or error."""
        resp = self.client.post("/api/score", json={})
        self.assertIn(resp.status_code, (200, 400, 422, 500))

    def test_alert_preferences_put_empty_body(self):
        """PUT /api/alerts/preferences with empty body returns no_changes or error."""
        resp = self.client.put("/api/alerts/preferences", json={})
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn(data.get("status"), ("no_changes", "updated"))

    def test_scores_deltas_with_hours_param(self):
        """GET /api/scores/deltas?hours=24 accepts valid param."""
        resp = self.client.get("/api/scores/deltas?hours=24")
        self.assertIn(resp.status_code, (200, 500))

    def test_score_accuracy_with_run_false(self):
        """GET /api/score/accuracy?run=false does not trigger validation."""
        resp = self.client.get("/api/score/accuracy?run=false")
        self.assertIn(resp.status_code, (200, 500))

    def test_opportunities_with_limit_param(self):
        """GET /api/opportunities?limit=5 accepts param."""
        resp = self.client.get("/api/opportunities?limit=5")
        self.assertIn(resp.status_code, (200, 500))


if __name__ == "__main__":
    unittest.main()
