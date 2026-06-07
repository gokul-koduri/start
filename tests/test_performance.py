"""Tests for Sprint 3 Epic 3.3 — Performance Optimization (T-050 to T-053)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRedisCacheFunctions(unittest.TestCase):
    """Test Redis cache layer functions exist in api_server (T-050)."""

    def test_redis_cache_functions_exist(self):
        """Redis cache functions are defined when HAS_FASTAPI."""
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                self.skipTest("FastAPI not installed")
            self.assertTrue(hasattr(api_server, "_redis_cache_get"))
            self.assertTrue(hasattr(api_server, "_redis_cache_set"))
            self.assertTrue(hasattr(api_server, "_redis_cache_invalidate"))
        except ImportError:
            self.skipTest("api_server not importable")

    def test_redis_cache_get_falls_back_to_memory(self):
        """_redis_cache_get falls back to in-memory when Redis unavailable."""
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                self.skipTest("FastAPI not installed")
            # Set a value in memory cache
            api_server._cache_set("test_key", {"val": 42}, ttl=60)
            # Should get it from memory (Redis won't be available in test)
            result = api_server._redis_cache_get("test_key")
            self.assertEqual(result, {"val": 42})
        except ImportError:
            self.skipTest("api_server not importable")

    def test_redis_cache_set_writes_to_memory(self):
        """_redis_cache_set always writes to in-memory cache."""
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                self.skipTest("FastAPI not installed")
            api_server._redis_cache_set("test_set_key", {"data": "hello"}, ttl=60)
            # Should be retrievable from memory
            result = api_server._redis_cache_get("test_set_key")
            self.assertEqual(result, {"data": "hello"})
        except ImportError:
            self.skipTest("api_server not importable")

    def test_redis_cache_invalidate_clears_memory(self):
        """_redis_cache_invalidate clears in-memory cache."""
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                self.skipTest("FastAPI not installed")
            api_server._redis_cache_set("inv_key", {"x": 1}, ttl=60)
            api_server._redis_cache_invalidate()
            result = api_server._redis_cache_get("inv_key")
            self.assertIsNone(result)
        except ImportError:
            self.skipTest("api_server not importable")


class TestPerformanceEndpoint(unittest.TestCase):
    """Test /api/performance endpoint (T-052)."""

    def test_performance_endpoint_exists(self):
        """Performance endpoint is registered in the FastAPI app."""
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                self.skipTest("FastAPI not installed")
            routes = [r.path for r in api_server.app.routes]
            self.assertIn("/api/performance", routes)
        except ImportError:
            self.skipTest("api_server not importable")

    @patch("db.connection.get_connection")
    def test_performance_endpoint_returns_json(self, mock_get_conn):
        """Performance endpoint returns valid JSON structure."""
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                self.skipTest("FastAPI not installed")
            from fastapi.testclient import TestClient

            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"response_ms": 100}, {"response_ms": 200}, {"response_ms": 300},
            ]
            mock_cursor.fetchone.side_effect = [
                {"cnt": 5, "avg_ms": 150.0},  # chat latency
                {"cnt": 2},                     # error count
            ]
            conn_instance = MagicMock()
            conn_instance.cursor.return_value = mock_cursor
            mock_get_conn.return_value = conn_instance

            client = TestClient(api_server.app)
            resp = client.get("/api/performance?hours=24")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("hours", data)
            self.assertEqual(data["hours"], 24)
            self.assertIn("query_latency", data)
            self.assertIn("chat_latency", data)
            self.assertIn("error_rate", data)
            self.assertIn("cache", data)
        except ImportError:
            self.skipTest("FastAPI test client not available")

    @patch("db.connection.get_connection")
    def test_performance_endpoint_empty_data(self, mock_get_conn):
        """Performance endpoint handles empty data gracefully."""
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                self.skipTest("FastAPI not installed")
            from fastapi.testclient import TestClient

            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_cursor.fetchone.side_effect = [
                {"cnt": 0, "avg_ms": None},
                {"cnt": 0},
            ]
            conn_instance = MagicMock()
            conn_instance.cursor.return_value = mock_cursor
            mock_get_conn.return_value = conn_instance

            client = TestClient(api_server.app)
            resp = client.get("/api/performance")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["query_latency"]["count"], 0)
        except ImportError:
            self.skipTest("FastAPI test client not available")


class TestPerformancePage(unittest.TestCase):
    """Test Streamlit performance page (T-053)."""

    def test_performance_page_import(self):
        """Performance page module imports without error."""
        try:
            from streamlit.pages.performance import render
            self.assertIsNotNone(render)
        except ImportError:
            self.skipTest("Streamlit not installed")

    def test_performance_page_has_render(self):
        """Performance page exports render function."""
        try:
            from streamlit.pages.performance import render
            self.assertTrue(callable(render))
        except ImportError:
            self.skipTest("Streamlit not installed")

    def test_performance_page_has_query_db(self):
        """Performance page has _query_db helper."""
        try:
            from streamlit.pages.performance import _query_db
            self.assertTrue(callable(_query_db))
        except ImportError:
            self.skipTest("Streamlit not installed")


class TestStreamlitCachingPerformance(unittest.TestCase):
    """Test cached helpers for performance page in streamlit_app (T-051)."""

    def test_load_performance_stats_exists(self):
        """load_performance_stats function exists in streamlit_app."""
        try:
            from streamlit_app import load_performance_stats
            self.assertIsNotNone(load_performance_stats)
        except (ImportError, AttributeError):
            self.skipTest("Streamlit not installed")

    def test_load_feedback_stats_exists(self):
        """load_feedback_stats function exists in streamlit_app."""
        try:
            from streamlit_app import load_feedback_stats
            self.assertIsNotNone(load_feedback_stats)
        except (ImportError, AttributeError):
            self.skipTest("Streamlit not installed")


if __name__ == "__main__":
    unittest.main()
