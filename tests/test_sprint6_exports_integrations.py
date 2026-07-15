"""Sprint 6 tests for export + integration endpoints (T-074 to T-078)."""

import unittest
from unittest.mock import patch, MagicMock


class _MockConn:
    def __init__(self, rows=None):
        self._rows = rows or []
        self._cursor = MagicMock()
        self._cursor.fetchall.return_value = self._rows

    def cursor(self):
        return self._cursor

    def close(self):
        pass


class TestSprint6ExportEndpoints(unittest.TestCase):
    """Validate new Sprint 6 export paths are registered and return expected types."""

    @patch("api.v2.export.schema.init_schema")
    @patch("api.v2.export.get_connection")
    def test_watchlist_csv_export(self, mock_conn, _mock_schema):
        from api.v2.export import export_watchlist_csv

        rows = [
            {
                "entity_name": "OpenAI",
                "entity_type": "company",
                "notes": "High momentum",
                "added_at": "2026-07-01 00:00:00",
                "composite_score": 91.2,
                "trend_direction": "rising",
            }
        ]
        mock_conn.return_value = _MockConn(rows)

        resp = export_watchlist_csv(1)
        self.assertEqual(resp.media_type, "text/csv")
        self.assertIn("watchlist_1_export.csv", resp.headers["content-disposition"])

    @patch("api.v2.export.schema.init_schema")
    @patch("api.v2.export.get_connection")
    def test_pdf_export(self, mock_conn, _mock_schema):
        from api.v2.export import export_pdf

        rows = [{"name": "OpenAI", "score": 91.2}]
        mock_conn.return_value = _MockConn(rows)

        resp = export_pdf("opportunity_scores", 10)
        self.assertEqual(resp.media_type, "application/pdf")
        self.assertIn("opportunity_scores_export.pdf", resp.headers["content-disposition"])


class TestSprint6WebhookIntegrations(unittest.TestCase):
    """Validate webhook dispatch + Zapier feed endpoints for Sprint 6."""

    @patch("api.v2.webhooks.schema.init_schema")
    @patch("api.v2.webhooks.get_connection")
    def test_zapier_new_alerts(self, mock_conn, _mock_schema):
        from api.v2.webhooks import zapier_new_alerts

        rows = [
            {
                "id": 1,
                "watchlist_id": 3,
                "alert_type": "score_change",
                "entity_name": "OpenAI",
                "old_score": 80.0,
                "new_score": 91.0,
                "delta": 11.0,
                "created_at": "2026-07-01 00:00:00",
                "watchlist_name": "AI Leaders",
            }
        ]
        mock_conn.return_value = _MockConn(rows)

        result = zapier_new_alerts(hours=24, limit=50)
        self.assertIn("alerts", result)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["hours"], 24)

    @patch("api.v2.webhooks.WebhookDispatcher")
    @patch("api.v2.webhooks.schema.init_schema")
    @patch("api.v2.webhooks.get_connection")
    def test_dispatch_event(self, mock_conn, _mock_schema, mock_dispatcher_cls):
        from api.v2.webhooks import dispatch_event

        rows = [
            {
                "id": 1,
                "url": "https://example.com/webhook",
                "events_json": '["score.updated"]',
                "headers_json": '{"X-Test": "1"}',
            }
        ]
        mock_conn.return_value = _MockConn(rows)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {
            "event_type": "score.updated",
            "registered": 1,
            "dispatched": 1,
            "results": [],
        }
        mock_dispatcher_cls.return_value = mock_dispatcher

        result = dispatch_event(event="score.updated", limit=100)
        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["event_type"], "score.updated")


if __name__ == "__main__":
    unittest.main()
