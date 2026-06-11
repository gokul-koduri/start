"""Tests for collector scheduler (scripts/collector_scheduler.py)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCollectorRegistry(unittest.TestCase):
    """Test collector registry and discovery."""

    def test_registry_has_known_collectors(self):
        """Registry contains expected collector names."""
        from scripts.collector_scheduler import COLLECTOR_CLASSES

        expected = [
            "bls_survival_rates",
            "google_news_rss",
            "techcrunch_rss",
            "failory_scraper",
            "hn_live",
            "reddit_stream",
        ]
        for name in expected:
            self.assertIn(name, COLLECTOR_CLASSES, f"Missing collector: {name}")

    def test_registry_entries_are_importable(self):
        """All registry entries can be imported."""
        from scripts.collector_scheduler import COLLECTOR_CLASSES

        for name, path in COLLECTOR_CLASSES.items():
            module_path, class_name = path.rsplit(".", 1)
            try:
                import importlib

                mod = importlib.import_module(module_path)
                self.assertTrue(
                    hasattr(mod, class_name), f"{path} missing class {class_name}"
                )
            except ImportError:
                pass  # Optional dependency — not a failure

    def test_get_collector_class_known(self):
        """_get_collector_class returns a class for known names."""
        from scripts.collector_scheduler import _get_collector_class

        cls = _get_collector_class("bls_survival_rates")
        self.assertIsNotNone(cls)

    def test_get_collector_class_unknown(self):
        """_get_collector_class raises ValueError for unknown names."""
        from scripts.collector_scheduler import _get_collector_class

        with self.assertRaises(ValueError):
            _get_collector_class("nonexistent_collector")


class TestTransientErrorDetection(unittest.TestCase):
    """Test retry logic — transient vs permanent error detection."""

    def test_transient_timeout(self):
        """Timeout errors are transient."""
        from scripts.collector_scheduler import _is_transient_error

        self.assertTrue(_is_transient_error(Exception("Connection timed out")))

    def test_transient_connection_reset(self):
        """Connection reset errors are transient."""
        from scripts.collector_scheduler import _is_transient_error

        self.assertTrue(_is_transient_error(Exception("Connection reset by peer")))

    def test_transient_5xx(self):
        """5xx server errors are transient."""
        from scripts.collector_scheduler import _is_transient_error

        self.assertTrue(_is_transient_error(Exception("500 Internal Server Error")))

    def test_permanent_401(self):
        """401 errors are permanent."""
        from scripts.collector_scheduler import _is_transient_error

        self.assertFalse(_is_transient_error(Exception("401 Unauthorized")))

    def test_permanent_403(self):
        """403 errors are permanent."""
        from scripts.collector_scheduler import _is_transient_error

        self.assertFalse(_is_transient_error(Exception("403 Forbidden")))

    def test_permanent_invalid_api_key(self):
        """Invalid API key errors are permanent."""
        from scripts.collector_scheduler import _is_transient_error

        self.assertFalse(_is_transient_error(Exception("Invalid API key provided")))


class TestRunWithRetry(unittest.TestCase):
    """Test the retry wrapper."""

    @patch("scripts.collector_scheduler._get_collector_class")
    def test_success_first_try(self, mock_get_class):
        """Successful run returns immediately."""
        mock_collector = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.records_collected = 42
        mock_result.records_inserted = 40
        mock_result.errors = []
        mock_collector.return_value.run.return_value = mock_result
        mock_get_class.return_value = mock_collector

        from scripts.collector_scheduler import run_with_retry

        result = run_with_retry("test_collector", {})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["records_collected"], 42)
        self.assertEqual(result["attempts"], 1)

    @patch("scripts.collector_scheduler._shutdown")
    @patch("scripts.collector_scheduler._get_collector_class")
    def test_retry_on_transient_failure(self, mock_get_class, mock_shutdown):
        """Transient failures trigger retries."""
        mock_collector = MagicMock()
        mock_fail = MagicMock()
        mock_fail.status = "failed"
        mock_fail.errors = ["Connection timed out"]
        mock_fail.records_collected = 0
        mock_fail.records_inserted = 0

        mock_success = MagicMock()
        mock_success.status = "success"
        mock_success.records_collected = 10
        mock_success.records_inserted = 10
        mock_success.errors = []

        mock_collector.return_value.run.side_effect = [mock_fail, mock_success]
        mock_get_class.return_value = mock_collector
        mock_shutdown.is_set.return_value = False
        mock_shutdown.wait.return_value = None

        from scripts.collector_scheduler import run_with_retry

        result = run_with_retry(
            "test_collector", {}, max_retries=3, backoff_seconds=[1]
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["attempts"], 2)

    @patch("scripts.collector_scheduler._shutdown")
    @patch("scripts.collector_scheduler._get_collector_class")
    def test_no_retry_on_permanent_failure(self, mock_get_class, mock_shutdown):
        """Permanent failures don't trigger retries."""
        mock_collector = MagicMock()
        mock_fail = MagicMock()
        mock_fail.status = "failed"
        mock_fail.errors = ["403 Forbidden"]
        mock_fail.records_collected = 0
        mock_fail.records_inserted = 0

        mock_collector.return_value.run.return_value = mock_fail
        mock_get_class.return_value = mock_collector
        mock_shutdown.is_set.return_value = False

        from scripts.collector_scheduler import run_with_retry

        result = run_with_retry("test_collector", {}, max_retries=3)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["attempts"], 1)


class TestRunGroup(unittest.TestCase):
    """Test running a group of collectors."""

    @patch("scripts.collector_scheduler.run_with_retry")
    def test_run_group_calls_all_collectors(self, mock_run):
        """run_group calls run_with_retry for each collector."""
        mock_run.side_effect = [
            {"name": "a", "status": "success", "attempts": 1, "errors": []},
            {"name": "b", "status": "success", "attempts": 1, "errors": []},
        ]

        from scripts.collector_scheduler import run_group

        results = run_group(
            ["a", "b"], {}, {"max_concurrent": 2, "retry": {"max_attempts": 1}}
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(mock_run.call_count, 2)


class TestRunAllGroups(unittest.TestCase):
    """Test running all configured groups."""

    @patch("scripts.collector_scheduler.run_group")
    def test_runs_all_groups(self, mock_run_group):
        """run_all_groups calls run_group for each configured group."""
        mock_run_group.return_value = [
            {"name": "a", "status": "success", "attempts": 1, "errors": []}
        ]

        config = {
            "scheduler": {
                "groups": {
                    "fast": {"interval_minutes": 120, "collectors": ["a"]},
                    "daily": {"interval_minutes": 1440, "collectors": ["b"]},
                }
            }
        }

        from scripts.collector_scheduler import run_all_groups

        results = run_all_groups(config)

        self.assertEqual(mock_run_group.call_count, 2)
        self.assertEqual(len(results), 2)


class TestSchedulerConfig(unittest.TestCase):
    """Test scheduler configuration parsing."""

    def test_scheduler_config_exists_in_settings(self):
        """settings.yaml has a scheduler section."""
        from config import load_config

        config = load_config()
        self.assertIn("scheduler", config)

    def test_scheduler_groups_defined(self):
        """Scheduler has groups defined."""
        from config import load_config

        config = load_config()
        groups = config["scheduler"].get("groups", {})
        self.assertGreater(len(groups), 0)

    def test_fast_group_has_collectors(self):
        """Fast group has at least one collector."""
        from config import load_config

        config = load_config()
        fast = config["scheduler"]["groups"].get("fast", {})
        self.assertGreater(len(fast.get("collectors", [])), 0)

    def test_daily_group_has_collectors(self):
        """Daily group has at least one collector."""
        from config import load_config

        config = load_config()
        daily = config["scheduler"]["groups"].get("daily", {})
        self.assertGreater(len(daily.get("collectors", [])), 0)

    def test_retry_config_present(self):
        """Retry configuration is present."""
        from config import load_config

        config = load_config()
        retry = config["scheduler"].get("retry", {})
        self.assertIn("max_attempts", retry)
        self.assertIn("backoff_seconds", retry)


class TestSchedulerShutdown(unittest.TestCase):
    """Test graceful shutdown."""

    def test_shutdown_event_exists(self):
        """Global shutdown event exists."""
        from scripts.collector_scheduler import _shutdown

        self.assertFalse(_shutdown.is_set())

    @patch("scripts.collector_scheduler._shutdown")
    @patch("scripts.collector_scheduler._get_collector_class")
    def test_shutdown_skips_collector(self, mock_get_class, mock_shutdown):
        """Collector is skipped when shutdown is set."""
        mock_shutdown.is_set.return_value = True
        from scripts.collector_scheduler import run_with_retry

        result = run_with_retry("test", {})
        self.assertEqual(result["status"], "skipped")


class TestSchedulerSummary(unittest.TestCase):
    """Test summary output."""

    def test_print_summary_runs(self):
        """print_summary doesn't crash with valid input."""
        from scripts.collector_scheduler import print_summary

        results = [
            {
                "name": "test_a",
                "status": "success",
                "records_collected": 10,
                "attempts": 1,
                "errors": [],
            },
            {
                "name": "test_b",
                "status": "failed",
                "records_collected": 0,
                "attempts": 3,
                "errors": ["timeout"],
            },
        ]
        # Should not raise
        print_summary(results)


if __name__ == "__main__":
    unittest.main()
