"""Watchlist alert agent tests — validates score delta detection and alert generation (T-113)."""

import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWatchlistAlertAgent(unittest.TestCase):
    """Test watchlist alert agent."""

    def test_agent_has_name(self):
        """Agent name should be 'watchlist_alert'."""
        from agents.watchlist_alert_agent import WatchlistAlertAgent

        agent = WatchlistAlertAgent(config={}, dry_run=True)
        self.assertEqual(agent.name, "watchlist_alert")

    def test_agent_instantiation(self):
        """Agent should instantiate with config."""
        from agents.watchlist_alert_agent import WatchlistAlertAgent

        agent = WatchlistAlertAgent(config={"lookback_hours": 12}, dry_run=True)
        self.assertIsNotNone(agent)

    def test_parse_alert_config_defaults(self):
        """Should return defaults when config is null."""
        from agents.watchlist_alert_agent import _parse_alert_config

        config = _parse_alert_config(None)
        self.assertEqual(config["min_delta"], 5.0)
        self.assertTrue(config["alert_on_trend_change"])

    def test_parse_alert_config_custom(self):
        """Should parse custom config JSON."""
        from agents.watchlist_alert_agent import _parse_alert_config
        import json

        raw = json.dumps({"min_delta": 10.0, "channels": ["slack"]})
        config = _parse_alert_config(raw)
        self.assertEqual(config["min_delta"], 10.0)
        self.assertEqual(config["channels"], ["slack"])

    def test_parse_alert_config_invalid_json(self):
        """Should return defaults on invalid JSON."""
        from agents.watchlist_alert_agent import _parse_alert_config

        config = _parse_alert_config("not json")
        self.assertEqual(config["min_delta"], 5.0)

    def test_resolves_from_orchestrator(self):
        """Agent should be resolvable from orchestrator registry."""
        from agents.orchestrator import _get_agent_class

        cls = _get_agent_class("watchlist_alert")
        self.assertIsNotNone(cls)
        self.assertEqual(cls.__name__, "WatchlistAlertAgent")

    @patch("agents.watchlist_alert_agent.get_connection")
    def test_execute_no_watchlists(self, mock_conn):
        """Should succeed with 0 alerts when no watchlists exist."""
        from agents.watchlist_alert_agent import WatchlistAlertAgent

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # No watchlist items
        mock_cursor.fetchone.return_value = None

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        agent = WatchlistAlertAgent(config={}, dry_run=True)
        result = agent.execute()

        self.assertEqual(result.status, "success")
        self.assertEqual(result.data["alerts_generated"], 0)

    @patch("agents.watchlist_alert_agent.get_connection")
    def test_execute_with_matching_deltas(self, mock_conn):
        """Should generate alerts when deltas match watched entities."""
        from agents.watchlist_alert_agent import WatchlistAlertAgent

        wl_rows = [
            {
                "watchlist_id": 1,
                "user_id": 1,
                "name": "Tech",
                "alert_config_json": None,
                "entity_name": "OpenAI",
                "entity_type": "company",
            },
        ]
        delta_rows = [
            {
                "entity_name": "OpenAI",
                "entity_type": "company",
                "old_score": 80.0,
                "new_score": 90.0,
                "delta": 10.0,
                "trend_previous": "stable",
                "trend_current": "rising",
                "signal_breakdown_json": None,
                "detected_at": "2026-01-01",
            },
        ]

        mock_cursor = MagicMock()
        # First call: watchlist items
        mock_cursor.fetchall.side_effect = [wl_rows, delta_rows]
        # Dedup check: no existing alert
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 1

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        agent = WatchlistAlertAgent(config={}, dry_run=True)
        result = agent.execute()

        self.assertEqual(result.status, "success")
        self.assertEqual(result.data["alerts_generated"], 1)
        self.assertEqual(result.data["watchlists_affected"], 1)

    @patch("agents.watchlist_alert_agent.get_connection")
    def test_execute_skips_below_threshold(self, mock_conn):
        """Should not alert when delta is below min_delta threshold."""
        from agents.watchlist_alert_agent import WatchlistAlertAgent
        import json

        wl_rows = [
            {
                "watchlist_id": 1,
                "user_id": 1,
                "name": "Tech",
                "alert_config_json": json.dumps({"min_delta": 20.0}),
                "entity_name": "OpenAI",
                "entity_type": "company",
            },
        ]
        delta_rows = [
            {
                "entity_name": "OpenAI",
                "entity_type": "company",
                "old_score": 80.0,
                "new_score": 90.0,
                "delta": 10.0,
                "trend_previous": "stable",
                "trend_current": "rising",
                "signal_breakdown_json": None,
                "detected_at": "2026-01-01",
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [wl_rows, delta_rows]
        mock_cursor.fetchone.return_value = None

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        agent = WatchlistAlertAgent(config={}, dry_run=True)
        result = agent.execute()

        self.assertEqual(result.status, "success")
        self.assertEqual(result.data["alerts_generated"], 0)


if __name__ == "__main__":
    unittest.main()
