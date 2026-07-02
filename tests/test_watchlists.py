"""Watchlist API tests — validates CRUD, auth enforcement, ownership (T-111)."""

import unittest
import sys
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class _MockCursor:
    """Minimal mock cursor that simulates DB operations."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self._rowcount = len(rows) if rows else 0
        self.lastrowid = 1
        self._results = list(rows) if rows else []

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        if self._results:
            return self._results.pop(0)
        return None

    def fetchall(self):
        results = self._results
        self._results = []
        return results

    @property
    def rowcount(self):
        return self._rowcount

    def close(self):
        pass


class _MockConn:
    """Minimal mock connection."""

    def __init__(self, cursor=None):
        self._cursor = cursor or _MockCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def _make_user(user_id=1, email="test@example.com", role="analyst"):
    return {
        "user_id": user_id,
        "email": email,
        "role": role,
        "auth_method": "jwt",
    }


class TestWatchlistRouter(unittest.TestCase):
    """Test watchlist CRUD endpoints using dependency override."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
            from api_server import app
            from auth.auth_middleware import get_current_user

            cls.app = app
            cls._original_override = getattr(app, "dependency_overrides", {}).copy()
        except ImportError:
            raise unittest.SkipTest("FastAPI not installed")

    def tearDown(self):
        # Clean up dependency overrides after each test
        self.app.dependency_overrides = getattr(self, "_original_override", {}).copy()

    def _get_client(self, user=None):
        from fastapi.testclient import TestClient
        from auth.auth_middleware import get_current_user

        if user:
            self.app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(self.app)

    def test_list_requires_auth(self):
        """GET /api/v2/watchlists returns 401 without auth."""
        client = self._get_client()
        resp = client.get("/api/v2/watchlists")
        self.assertEqual(resp.status_code, 401)

    def test_create_requires_auth(self):
        """POST /api/v2/watchlists returns 401 without auth."""
        client = self._get_client()
        resp = client.post("/api/v2/watchlists", json={"name": "Test"})
        self.assertEqual(resp.status_code, 401)

    def test_get_requires_auth(self):
        """GET /api/v2/watchlists/1 returns 401 without auth."""
        client = self._get_client()
        resp = client.get("/api/v2/watchlists/1")
        self.assertEqual(resp.status_code, 401)

    def test_delete_requires_auth(self):
        """DELETE /api/v2/watchlists/1 returns 401 without auth."""
        client = self._get_client()
        resp = client.delete("/api/v2/watchlists/1")
        self.assertEqual(resp.status_code, 401)

    @patch("api.v2.watchlists.get_connection")
    def test_list_watchlists_success(self, mock_conn):
        """GET /api/v2/watchlists returns user's watchlists."""
        mock_cursor = _MockCursor(
            [
                {"cnt": 1},
                {
                    "id": 1,
                    "user_id": 1,
                    "name": "Tech Startups",
                    "description": "AI companies",
                    "is_active": 1,
                    "alert_config_json": None,
                    "item_count": 3,
                    "created_at": "2026-01-01",
                    "updated_at": "2026-01-01",
                },
            ]
        )
        mock_conn.return_value = _MockConn(mock_cursor)

        client = self._get_client(user=_make_user(user_id=1))
        resp = client.get("/api/v2/watchlists")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("watchlists", data)
        self.assertEqual(data["total"], 1)

    @patch("api.v2.watchlists.get_connection")
    def test_create_watchlist(self, mock_conn):
        """POST /api/v2/watchlists creates a new watchlist."""
        mock_cursor = _MockCursor(
            [
                {
                    "id": 1,
                    "user_id": 1,
                    "name": "My List",
                    "description": "Test list",
                    "is_active": 1,
                    "alert_config_json": None,
                    "created_at": "2026-01-01",
                    "updated_at": "2026-01-01",
                },
            ]
        )
        mock_cursor.lastrowid = 1
        mock_conn.return_value = _MockConn(mock_cursor)

        client = self._get_client(user=_make_user(user_id=1))
        resp = client.post(
            "/api/v2/watchlists",
            json={"name": "My List", "description": "Test list"},
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("watchlist", data)
        self.assertEqual(data["watchlist"]["name"], "My List")

    @patch("api.v2.watchlists.get_connection")
    def test_add_item_to_watchlist(self, mock_conn):
        """POST /api/v2/watchlists/1/items adds an entity."""
        wl_row = {
            "id": 1,
            "user_id": 1,
            "name": "Test",
            "description": None,
            "is_active": 1,
            "alert_config_json": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        item_row = {
            "id": 1,
            "watchlist_id": 1,
            "entity_name": "OpenAI",
            "entity_type": "company",
            "notes": None,
            "added_at": "2026-01-01",
        }

        mock_cursor = _MockCursor([wl_row, item_row])
        mock_cursor.lastrowid = 1
        mock_conn.return_value = _MockConn(mock_cursor)

        client = self._get_client(user=_make_user(user_id=1))
        resp = client.post(
            "/api/v2/watchlists/1/items",
            json={"entity_name": "OpenAI", "entity_type": "company"},
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("item", data)
        self.assertEqual(data["item"]["entity_name"], "OpenAI")

    @patch("api.v2.watchlists.get_connection")
    def test_remove_item(self, mock_conn):
        """DELETE /api/v2/watchlists/1/items/1 removes an entity."""
        wl_row = {
            "id": 1,
            "user_id": 1,
            "name": "Test",
            "description": None,
            "is_active": 1,
            "alert_config_json": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        mock_cursor = _MockCursor([wl_row])
        mock_cursor._rowcount = 1
        mock_conn.return_value = _MockConn(mock_cursor)

        client = self._get_client(user=_make_user(user_id=1))
        resp = client.delete("/api/v2/watchlists/1/items/1")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["deleted"])

    @patch("api.v2.watchlists.get_connection")
    def test_alert_history(self, mock_conn):
        """GET /api/v2/watchlists/1/alerts returns alert history."""
        wl_row = {
            "id": 1,
            "user_id": 1,
            "name": "Test",
            "description": None,
            "is_active": 1,
            "alert_config_json": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        cnt_row = {"cnt": 1}
        alert_row = {
            "id": 1,
            "watchlist_id": 1,
            "alert_type": "score_change",
            "entity_name": "OpenAI",
            "old_score": 80.0,
            "new_score": 90.0,
            "delta": 10.0,
            "alert_data_json": None,
            "created_at": "2026-01-01",
        }

        mock_cursor = _MockCursor([wl_row, cnt_row, alert_row])
        mock_conn.return_value = _MockConn(mock_cursor)

        client = self._get_client(user=_make_user(user_id=1))
        resp = client.get("/api/v2/watchlists/1/alerts")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("alerts", data)

    @patch("api.v2.watchlists.get_connection")
    def test_update_alert_config(self, mock_conn):
        """PUT /api/v2/watchlists/1/alert-config updates thresholds."""
        wl_row = {
            "id": 1,
            "user_id": 1,
            "name": "Test",
            "description": None,
            "is_active": 1,
            "alert_config_json": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        config_row = {"alert_config_json": json.dumps({"min_delta": 5.0})}

        mock_cursor = _MockCursor([wl_row, config_row])
        mock_conn.return_value = _MockConn(mock_cursor)

        client = self._get_client(user=_make_user(user_id=1))
        resp = client.put(
            "/api/v2/watchlists/1/alert-config",
            json={"min_delta": 10.0, "channels": ["email", "slack"]},
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("alert_config", data)
        self.assertEqual(data["alert_config"]["min_delta"], 10.0)

    @patch("api.v2.watchlists.get_connection")
    def test_ownership_enforcement(self, mock_conn):
        """Users can't access other users' watchlists."""
        mock_cursor = _MockCursor([])  # No rows = not found
        mock_conn.return_value = _MockConn(mock_cursor)

        client = self._get_client(user=_make_user(user_id=2))
        resp = client.get("/api/v2/watchlists/1")

        self.assertEqual(resp.status_code, 404)


class TestWatchlistSchema(unittest.TestCase):
    """Test that schema includes watchlist tables."""

    def test_schema_version_bumped(self):
        """Schema version should be 24."""
        from db.schema import get_schema_version

        self.assertEqual(get_schema_version(), 24)

    def test_watchlist_tables_in_schema(self):
        """Watchlist tables should be in _TABLES."""
        from db.schema import _TABLES

        table_sql = " ".join(_TABLES)
        self.assertIn("watchlists", table_sql)
        self.assertIn("watchlist_items", table_sql)
        self.assertIn("watchlist_alert_history", table_sql)


if __name__ == "__main__":
    unittest.main()
