"""Tests for Sprint 3 Epic 3.1 — Feedback Dashboard (T-043 to T-046)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFeedbackAnalyzerAgent(unittest.TestCase):
    """Test the feedback analyzer agent (T-044)."""

    def test_import_feedback_analyzer(self):
        """Feedback analyzer agent imports without error."""
        from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent
        self.assertIsNotNone(FeedbackAnalyzerAgent)

    def test_feedback_analyzer_name(self):
        """Agent name is feedback_analyzer."""
        from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent
        agent = FeedbackAnalyzerAgent(config={})
        self.assertEqual(agent.name, "feedback_analyzer")

    def test_feedback_analyzer_inherits_base_agent(self):
        """Agent inherits from BaseAgent."""
        from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent
        from agents.base import BaseAgent
        self.assertTrue(issubclass(FeedbackAnalyzerAgent, BaseAgent))

    @patch("db.connection.get_connection")
    def test_feedback_analyzer_execute_success(self, mock_get_conn):
        """Agent executes and writes analysis."""
        from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.side_effect = [
            {"cnt": 0, "avg": None},  # rating stats
            {"cnt": 0},  # total_queries
            {"cnt": 0},  # total_chats
            {"cnt": 0},  # total_feedback
        ]
        conn_instance = MagicMock()
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        agent = FeedbackAnalyzerAgent(config={})
        result = agent.execute()
        self.assertEqual(result.status, "success")
        self.assertIn("analysis_week", result.data)

    @patch("db.connection.get_connection")
    def test_feedback_analyzer_execute_failure(self, mock_get_conn):
        """Agent returns failed status on DB error."""
        from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent

        mock_get_conn.side_effect = Exception("DB connection failed")

        agent = FeedbackAnalyzerAgent(config={})
        result = agent.execute()
        self.assertEqual(result.status, "failed")
        self.assertIn("DB connection failed", result.errors)


class TestOrchestratorFeedbackCheck(unittest.TestCase):
    """Test orchestrator feedback priority check (T-045)."""

    def test_feedback_analyzer_registered_in_orchestrator(self):
        """Orchestrator can load feedback_analyzer agent."""
        from agents.orchestrator import _get_agent_class
        agent_class = _get_agent_class("feedback_analyzer")
        self.assertIsNotNone(agent_class)

    @patch("db.connection.get_connection")
    def test_check_feedback_priorities_with_data(self, mock_get_conn):
        """Orchestrator reads feedback priorities."""
        from agents.orchestrator import OrchestratorAgent
        import json

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "trending_queries": json.dumps([{"query": "AI startups", "count": 50}]),
            "top_feature_requests": json.dumps([{"feature": "Slack alerts", "upvotes": 10}]),
        }
        conn_instance = MagicMock()
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        orchestrator = OrchestratorAgent(config={})
        priorities = orchestrator._check_feedback_priorities()
        self.assertIsInstance(priorities, dict)
        self.assertIn("trending_themes", priorities)

    @patch("db.connection.get_connection")
    def test_check_feedback_priorities_empty(self, mock_get_conn):
        """Returns empty dict when no feedback analysis exists."""
        from agents.orchestrator import OrchestratorAgent

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        conn_instance = MagicMock()
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        orchestrator = OrchestratorAgent(config={})
        priorities = orchestrator._check_feedback_priorities()
        self.assertEqual(priorities, {})

    @patch("db.connection.get_connection")
    def test_check_feedback_priorities_db_error(self, mock_get_conn):
        """Returns empty dict on DB error (best-effort)."""
        from agents.orchestrator import OrchestratorAgent

        mock_get_conn.side_effect = Exception("Connection refused")

        orchestrator = OrchestratorAgent(config={})
        priorities = orchestrator._check_feedback_priorities()
        self.assertEqual(priorities, {})


class TestWeeklyReport(unittest.TestCase):
    """Test the weekly report script (T-046)."""

    def test_import_weekly_report(self):
        """Weekly report module imports."""
        from scripts.weekly_report import generate_report
        self.assertIsNotNone(generate_report)

    @patch("db.connection.get_connection")
    @patch("db.schema.init_schema")
    def test_generate_report_returns_markdown(self, mock_init, mock_get_conn):
        """Report generation returns markdown string."""
        from scripts.weekly_report import generate_report

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            None,          # analysis
            {"cnt": 5},    # queries_week
            {"cnt": 3},    # chats_week
            {"cnt": 2},    # feedback_week
        ]
        mock_cursor.fetchall.side_effect = [
            [],  # top_queries
            [],  # top_features
        ]
        conn_instance = MagicMock()
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        report = generate_report()
        self.assertIn("Weekly Feedback Report", report)
        self.assertIn("Summary", report)

    @patch("db.connection.get_connection")
    @patch("db.schema.init_schema")
    def test_generate_report_with_queries(self, mock_init, mock_get_conn):
        """Report includes top queries when present."""
        from scripts.weekly_report import generate_report

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            None,
            {"cnt": 10},
            {"cnt": 5},
            {"cnt": 3},
        ]
        mock_cursor.fetchall.side_effect = [
            [{"query": "AI startups", "count": 42}],
            [],
        ]
        conn_instance = MagicMock()
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        report = generate_report()
        self.assertIn("AI startups", report)

    @patch("db.connection.get_connection")
    @patch("db.schema.init_schema")
    def test_generate_report_with_output_file(self, mock_init, mock_get_conn):
        """Report can be written to file."""
        from scripts.weekly_report import generate_report
        import tempfile

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            None, {"cnt": 0}, {"cnt": 0}, {"cnt": 0},
        ]
        mock_cursor.fetchall.side_effect = [[], []]
        conn_instance = MagicMock()
        conn_instance.cursor.return_value = mock_cursor
        mock_get_conn.return_value = conn_instance

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = f.name

        report = generate_report(output_path=path)
        self.assertTrue(Path(path).exists())
        self.assertTrue(Path(path).stat().st_size > 0)
        Path(path).unlink()


class TestStreamlitFeedbackPage(unittest.TestCase):
    """Test feedback page module can be imported (T-043)."""

    def test_feedback_page_import(self):
        """Streamlit feedback page module imports."""
        from streamlit.pages.feedback import render
        self.assertIsNotNone(render)

    def test_feedback_page_has_render(self):
        """Feedback page exports render function."""
        from streamlit.pages.feedback import render
        self.assertTrue(callable(render))

    def test_feedback_page_has_query_db(self):
        """Feedback page has _query_db helper."""
        from streamlit.pages.feedback import _query_db
        self.assertTrue(callable(_query_db))


class TestSchemaV21(unittest.TestCase):
    """Test schema version 21 changes."""

    def test_schema_version_is_21(self):
        """Schema version is 21."""
        from db.schema import get_schema_version
        self.assertEqual(get_schema_version(), 21)

    def test_feedback_analysis_table_in_schema(self):
        """feedback_analysis table exists in schema."""
        from db.schema import _TABLES
        table_sql = " ".join(_TABLES)
        self.assertIn("feedback_analysis", table_sql)

    def test_error_log_table_in_schema(self):
        """error_log table exists in schema."""
        from db.schema import _TABLES
        table_sql = " ".join(_TABLES)
        self.assertIn("error_log", table_sql)

    def test_feedback_analysis_has_key_columns(self):
        """feedback_analysis has key columns."""
        from db.schema import _TABLES
        for t in _TABLES:
            if "feedback_analysis" in t:
                self.assertIn("analysis_week", t)
                self.assertIn("trending_queries", t)
                self.assertIn("calibration_gaps", t)
                self.assertIn("avg_rating", t)
                break

    def test_error_log_has_key_columns(self):
        """error_log has key columns."""
        from db.schema import _TABLES
        for t in _TABLES:
            if "error_log" in t:
                self.assertIn("fingerprint", t)
                self.assertIn("traceback_text", t)
                self.assertIn("endpoint", t)
                self.assertIn("severity", t)
                break


class TestStreamlitCaching(unittest.TestCase):
    """Test Streamlit cached helpers (T-051 partial)."""

    def test_load_feedback_stats_exists(self):
        """load_feedback_stats function exists in streamlit_app."""
        try:
            from streamlit_app import load_feedback_stats
            self.assertIsNotNone(load_feedback_stats)
        except (ImportError, AttributeError):
            self.skipTest("Streamlit not installed")

    def test_load_performance_stats_exists(self):
        """load_performance_stats function exists in streamlit_app."""
        try:
            from streamlit_app import load_performance_stats
            self.assertIsNotNone(load_performance_stats)
        except (ImportError, AttributeError):
            self.skipTest("Streamlit not installed")


if __name__ == "__main__":
    unittest.main()
