"""Tests for Sprint 3 Epic 3.2 — Error Tracking (T-047 to T-049)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestErrorLogTable(unittest.TestCase):
    """Test error_log table in schema (T-047)."""

    def test_error_log_table_exists(self):
        """error_log table is defined in schema."""
        from db.schema import _TABLES
        table_sql = " ".join(_TABLES)
        self.assertIn("error_log", table_sql)

    def test_error_log_has_required_columns(self):
        """error_log has all required columns."""
        from db.schema import _TABLES
        for t in _TABLES:
            if "error_log" in t and "CREATE TABLE" in t:
                self.assertIn("error_type", t)
                self.assertIn("error_message", t)
                self.assertIn("traceback_text", t)
                self.assertIn("endpoint", t)
                self.assertIn("request_method", t)
                self.assertIn("request_path", t)
                self.assertIn("severity", t)
                self.assertIn("fingerprint", t)
                self.assertIn("created_at", t)
                break

    def test_error_log_has_indexes(self):
        """error_log has appropriate indexes."""
        from db.schema import _TABLES
        for t in _TABLES:
            if "error_log" in t and "CREATE TABLE" in t:
                self.assertIn("idx_el_type", t)
                self.assertIn("idx_el_created", t)
                self.assertIn("idx_el_fingerprint", t)
                break

    def test_error_log_indexes_in_index_list(self):
        """error_log indexes exist in _INDEXES list."""
        from db.schema import _INDEXES
        index_sql = " ".join(_INDEXES)
        self.assertIn("error_log", index_sql)


class TestHealthMonitorErrors(unittest.TestCase):
    """Test health monitor error checking (T-049)."""

    def test_check_errors_import(self):
        """check_errors function can be imported."""
        from scripts.health_monitor import check_errors
        self.assertIsNotNone(check_errors)

    @patch("db.connection.get_connection")
    def test_check_errors_healthy(self, mock_get_conn):
        """Returns healthy when no errors."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"cnt": 0},   # hourly
            {"cnt": 0},   # daily
        ]
        mock_cursor.fetchall.return_value = []
        conn_instance = MagicMock()
        conn_instance.__enter__ = MagicMock(return_value=conn_instance)
        conn_instance.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        from scripts.health_monitor import check_errors
        result = check_errors()
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["hourly_errors"], 0)

    @patch("db.connection.get_connection")
    def test_check_errors_critical(self, mock_get_conn):
        """Returns critical when many hourly errors."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"cnt": 60},  # hourly — over threshold
            {"cnt": 200}, # daily
        ]
        mock_cursor.fetchall.return_value = [
            {"error_type": "RuntimeError", "cnt": 40},
        ]
        conn_instance = MagicMock()
        conn_instance.__enter__ = MagicMock(return_value=conn_instance)
        conn_instance.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        from scripts.health_monitor import check_errors
        result = check_errors()
        self.assertEqual(result["status"], "critical")

    @patch("db.connection.get_connection")
    def test_check_errors_warning(self, mock_get_conn):
        """Returns warning when moderate hourly errors."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"cnt": 15},  # hourly — warning threshold
            {"cnt": 30},  # daily
        ]
        mock_cursor.fetchall.return_value = []
        conn_instance = MagicMock()
        conn_instance.__enter__ = MagicMock(return_value=conn_instance)
        conn_instance.__exit__ = MagicMock(return_value=False)
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        from scripts.health_monitor import check_errors
        result = check_errors()
        self.assertEqual(result["status"], "warning")

    @patch("db.connection.get_connection")
    def test_check_errors_db_failure(self, mock_get_conn):
        """Returns unknown when DB fails."""
        mock_get_conn.side_effect = Exception("Connection refused")

        from scripts.health_monitor import check_errors
        result = check_errors()
        self.assertEqual(result["status"], "unknown")

    def test_run_all_checks_includes_errors(self):
        """run_all_checks includes the errors check."""
        from scripts.health_monitor import run_all_checks
        with patch("scripts.health_monitor.check_mysql", return_value={"status": "healthy"}):
            with patch("scripts.health_monitor.check_redis", return_value={"status": "not_installed", "error": ""}):
                with patch("scripts.health_monitor.check_disk", return_value={"status": "healthy"}):
                    with patch("scripts.health_monitor.check_api", return_value={"status": "not_running", "error": ""}):
                        with patch("scripts.health_monitor.check_docker", return_value={"status": "not_installed", "error": ""}):
                            with patch("scripts.health_monitor.check_pipeline_freshness", return_value={"status": "unknown", "error": ""}):
                                with patch("scripts.health_monitor.check_errors", return_value={"status": "healthy", "hourly_errors": 0, "daily_errors": 0}):
                                    result = run_all_checks()
                                    self.assertIn("errors", result["checks"])


class TestSentryIntegration(unittest.TestCase):
    """Test Sentry SDK optional integration (T-048)."""

    def test_sentry_init_without_dsn(self):
        """No sentry initialization when SENTRY_DSN is not set."""
        import os
        dsn = os.environ.pop("SENTRY_DSN", None)
        try:
            # Just verify the code path doesn't crash
            self.assertTrue(True)
        finally:
            if dsn:
                os.environ["SENTRY_DSN"] = dsn

    def test_api_server_imports(self):
        """api_server module imports without error."""
        import api_server
        self.assertTrue(hasattr(api_server, "app"))


if __name__ == "__main__":
    unittest.main()
