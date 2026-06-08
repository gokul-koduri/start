"""Tests for the email queue and worker system."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEmailQueue(unittest.TestCase):
    """Test utils.email_queue module."""

    def test_import(self):
        """Test email_queue can be imported."""
        from utils.email_queue import queue_email, queue_bulk, queue_stats, render_template
        self.assertTrue(callable(queue_email))
        self.assertTrue(callable(queue_bulk))
        self.assertTrue(callable(queue_stats))
        self.assertTrue(callable(render_template))

    @patch("utils.email_queue.get_connection")
    @patch("utils.email_queue._is_suppressed", return_value=False)
    def test_queue_email_inserts_row(self, mock_suppressed, mock_conn):
        """Test that queue_email inserts into outbound_emails."""
        from utils.email_queue import queue_email

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)

        email_id = queue_email(
            recipient="test@example.com",
            subject="Test Subject",
            email_type="digest",
            plain_body="Hello plain",
            html_body="<p>Hello HTML</p>",
        )
        self.assertEqual(email_id, 42)
        # Verify INSERT was called
        mock_cursor.execute.assert_called()
        first_call_args = mock_cursor.execute.call_args_list[0]
        self.assertIn("INSERT INTO outbound_emails", first_call_args[0][0])

    @patch("utils.email_queue._is_suppressed", return_value=True)
    def test_queue_email_rejects_suppressed(self, mock_suppressed):
        """Test that queue_email raises ValueError for suppressed recipients."""
        from utils.email_queue import queue_email

        with self.assertRaises(ValueError) as ctx:
            queue_email(
                recipient="bounced@example.com",
                subject="Test",
                email_type="digest",
                plain_body="x",
                html_body="<p>x</p>",
            )
        self.assertIn("suppressed", str(ctx.exception))

    @patch("utils.email_queue._is_suppressed", return_value=False)
    @patch("utils.email_queue.get_connection")
    def test_queue_bulk_skips_suppressed(self, mock_conn, mock_suppressed):
        """Test that queue_bulk skips suppressed recipients silently."""
        from utils.email_queue import queue_bulk

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # First is not suppressed, second is
        mock_suppressed.side_effect = [False, True]
        ids = queue_bulk(
            ["ok@example.com", "bad@example.com"],
            subject="Test",
            email_type="digest",
            plain_body="x",
            html_body="<p>x</p>",
        )
        self.assertEqual(len(ids), 1)


class TestEmailWorker(unittest.TestCase):
    """Test agents.email_worker module."""

    def test_import(self):
        """Test email_worker can be imported."""
        from agents.email_worker import drain_queue, _build_mime
        self.assertTrue(callable(drain_queue))
        self.assertTrue(callable(_build_mime))

    @patch("agents.email_worker._get_smtp_config")
    def test_drain_queue_skips_without_smtp(self, mock_cfg):
        """Test drain_queue returns empty stats when SMTP not configured."""
        from agents.email_worker import drain_queue

        mock_cfg.return_value = {"host": "", "port": 587, "user": "", "password": "", "from_address": ""}
        stats = drain_queue()
        self.assertEqual(stats["sent"], 0)
        self.assertEqual(stats["skipped"], 0)

    def test_build_mime(self):
        """Test MIME message construction."""
        from agents.email_worker import _build_mime

        email_row = {
            "recipient": "test@example.com",
            "recipient_name": "Test User",
            "subject": "Test Subject",
            "plain_body": "Hello world",
            "html_body": "<p>Hello world</p>",
            "from_address": "noreply@example.com",
            "reply_to": None,
        }
        cfg = {"from_address": "noreply@example.com", "host": "smtp.example.com",
               "port": 587, "user": "", "password": ""}

        msg = _build_mime(email_row, cfg)

        self.assertEqual(msg["Subject"], "Test Subject")
        self.assertIn("test@example.com", msg["To"])
        self.assertIn("Test User", msg["To"])
        self.assertIsNotNone(msg["Message-ID"])
        self.assertIsNotNone(msg["Date"])

        # Verify multipart/alternative with plain + html
        parts = list(msg.walk())
        content_types = [p.get_content_type() for p in parts]
        self.assertIn("text/plain", content_types)
        self.assertIn("text/html", content_types)


class TestEmailTemplates(unittest.TestCase):
    """Test email template rendering."""

    def test_base_template_exists(self):
        """Test base.html template exists."""
        from utils.email_queue import _template_dir
        self.assertTrue((_template_dir / "base.html").exists())

    def test_digest_template_exists(self):
        """Test digest.html template exists."""
        from utils.email_queue import _template_dir
        self.assertTrue((_template_dir / "digest.html").exists())

    def test_report_template_exists(self):
        """Test report.html template exists."""
        from utils.email_queue import _template_dir
        self.assertTrue((_template_dir / "report.html").exists())

    def test_alert_template_exists(self):
        """Test alert.html template exists."""
        from utils.email_queue import _template_dir
        self.assertTrue((_template_dir / "alert.html").exists())

    def test_welcome_template_exists(self):
        """Test welcome.html template exists."""
        from utils.email_queue import _template_dir
        self.assertTrue((_template_dir / "welcome.html").exists())

    def test_render_template_fallback(self):
        """Test render_template handles missing templates gracefully."""
        from utils.email_queue import render_template
        result = render_template("nonexistent.html", {})
        self.assertIn("not found", result)

    def test_render_digest_basic(self):
        """Test rendering digest template with basic context."""
        from utils.email_queue import render_template
        html = render_template("digest.html", {
            "header_title": "Daily Digest",
            "header_subtitle": "June 6, 2026",
            "period_label": "daily",
            "total_startups": "163",
            "news_count": "42",
            "high_value_count": "12",
            "top_failures": [
                {"category": "Supply Chain", "count": 35},
                {"category": "Market Timing", "count": 22},
            ],
            "alerts": [],
            "collection_runs": [],
            "dashboard_url": "https://github.com/gokul-koduri/start",
            "unsubscribe_url": "#",
            "preferences_url": "#",
        })
        self.assertIn("Daily Digest", html)
        self.assertIn("163", html)
        self.assertIn("Supply Chain", html)

    def test_plain_from_html(self):
        """Test HTML to plain text conversion."""
        from utils.email_queue import plain_from_html
        html = "<h1>Title</h1><p>Hello world</p><table><tr><td>A</td><td>B</td></tr></table>"
        text = plain_from_html(html)
        self.assertIn("Title", text)
        self.assertIn("Hello world", text)
        self.assertNotIn("<h1>", text)
        self.assertNotIn("<table>", text)


class TestEmailDigestAgent(unittest.TestCase):
    """Test email digest agent (updated version)."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.email_digest_agent import EmailDigestAgent
        agent = EmailDigestAgent()
        self.assertEqual(agent.name, "email_digest")

    def test_agent_enabled_by_default(self):
        """Test agent is enabled by default."""
        from agents.email_digest_agent import EmailDigestAgent
        agent = EmailDigestAgent()
        self.assertTrue(agent.enabled)


class TestSchemaV23(unittest.TestCase):
    """Test that schema v23 includes email queue tables."""

    def test_schema_version_bumped(self):
        """Test schema version is 23."""
        from db.schema import get_schema_version
        self.assertEqual(get_schema_version(), 23)

    def test_email_tables_in_schema(self):
        """Test outbound_emails and related tables are defined."""
        from db.schema import _TABLES
        table_names = []
        for t in _TABLES:
            if "CREATE TABLE" in t:
                name = t.split("CREATE TABLE IF NOT EXISTS ")[1].split(" ")[0]
                table_names.append(name)
        self.assertIn("outbound_emails", table_names)
        self.assertIn("email_delivery_log", table_names)
        self.assertIn("email_suppressions", table_names)


if __name__ == "__main__":
    unittest.main()
