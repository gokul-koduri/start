"""Tests for alert consumer (scripts/alert_consumer.py)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBuildReason(unittest.TestCase):
    """Test _build_reason helper."""

    def test_reason_with_attribution(self):
        """Returns top signal info when attribution is present."""
        from scripts.alert_consumer import _build_reason

        alert = {
            "attribution": [
                {"signal_type": "funding_round", "contribution_pct": 45.0},
                {"signal_type": "github_trend", "contribution_pct": 30.0},
            ],
        }
        reason = _build_reason(alert)
        self.assertIn("funding_round", reason)
        self.assertIn("45", reason)

    def test_reason_without_attribution(self):
        """Returns generic reason when attribution is empty."""
        from scripts.alert_consumer import _build_reason

        alert = {"attribution": []}
        reason = _build_reason(alert)
        self.assertIn("threshold", reason.lower())

    def test_reason_with_non_list_attribution(self):
        """Handles non-list attribution gracefully."""
        from scripts.alert_consumer import _build_reason

        alert = {"attribution": "not a list"}
        reason = _build_reason(alert)
        self.assertIn("threshold", reason.lower())


class TestQuietHours(unittest.TestCase):
    """Test quiet hours detection."""

    def test_no_quiet_hours_configured(self):
        """Returns False when no quiet hours configured."""
        from scripts.alert_consumer import _is_quiet_hours

        prefs = {"quiet_hours_start": None, "quiet_hours_end": None}
        self.assertFalse(_is_quiet_hours(prefs))

    def test_invalid_quiet_hours_format(self):
        """Returns False for invalid time format."""
        from scripts.alert_consumer import _is_quiet_hours

        prefs = {"quiet_hours_start": "invalid", "quiet_hours_end": "08:00"}
        self.assertFalse(_is_quiet_hours(prefs))

    def test_valid_quiet_hours_check_runs(self):
        """Quiet hours check executes without error for valid format."""
        from scripts.alert_consumer import _is_quiet_hours

        prefs = {"quiet_hours_start": "22:00", "quiet_hours_end": "08:00"}
        # Just verify it doesn't crash — result depends on current time
        result = _is_quiet_hours(prefs)
        self.assertIsInstance(result, bool)


class TestLoadPreferences(unittest.TestCase):
    """Test preference loading."""

    def test_load_defaults_on_db_error(self):
        """Returns defaults when DB is unavailable."""
        from scripts.alert_consumer import _load_preferences

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("DB error")
        prefs = _load_preferences(mock_conn)
        self.assertTrue(prefs["email_enabled"])
        self.assertTrue(prefs["slack_enabled"])
        self.assertEqual(prefs["min_score_threshold"], 80.0)

    def test_load_defaults_on_empty_table(self):
        """Returns defaults when no preferences exist."""
        from scripts.alert_consumer import _load_preferences

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        prefs = _load_preferences(mock_conn)
        self.assertTrue(prefs["email_enabled"])
        self.assertEqual(prefs["min_score_threshold"], 80.0)

    def test_load_from_db(self):
        """Loads preferences from database row."""
        from scripts.alert_consumer import _load_preferences

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "email_enabled": 0,
            "slack_enabled": 1,
            "discord_enabled": 1,
            "webhook_enabled": 1,
            "min_score_threshold": 90.0,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "max_alerts_per_hour": 10,
        }
        mock_conn.cursor.return_value = mock_cursor
        prefs = _load_preferences(mock_conn)
        self.assertFalse(prefs["email_enabled"])
        self.assertTrue(prefs["slack_enabled"])
        self.assertEqual(prefs["min_score_threshold"], 90.0)


class TestWebhookDispatch(unittest.TestCase):
    """Test webhook dispatch."""

    @patch("scripts.alert_consumer.urllib.request.urlopen")
    def test_slack_webhook_success(self, mock_urlopen):
        """Slack webhook returns sent on success."""
        from scripts.alert_consumer import _send_slack

        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock())
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        alert = {
            "entity_name": "TestCorp",
            "composite_score": 85.0,
            "trend_direction": "up",
            "signal_count": 5,
            "entity_type": "company",
        }
        status, error = _send_slack("https://hooks.slack.com/test", alert)
        self.assertEqual(status, "sent")
        self.assertIsNone(error)

    @patch("scripts.alert_consumer.urllib.request.urlopen")
    def test_slack_webhook_failure(self, mock_urlopen):
        """Slack webhook returns failed on error."""
        from scripts.alert_consumer import _send_slack

        mock_urlopen.side_effect = Exception("Connection refused")
        alert = {
            "entity_name": "TestCorp",
            "composite_score": 85.0,
            "trend_direction": "up",
            "signal_count": 5,
            "entity_type": "company",
        }
        status, error = _send_slack("https://hooks.slack.com/test", alert)
        self.assertEqual(status, "failed")
        self.assertIn("Connection refused", error)

    @patch("scripts.alert_consumer.urllib.request.urlopen")
    def test_discord_webhook_success(self, mock_urlopen):
        """Discord webhook returns sent on success."""
        from scripts.alert_consumer import _send_discord

        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock())
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        alert = {
            "entity_name": "TestCorp",
            "composite_score": 92.0,
            "trend_direction": "up",
            "signal_count": 3,
        }
        status, error = _send_discord("https://discord.com/api/webhooks/test", alert)
        self.assertEqual(status, "sent")

    @patch("scripts.alert_consumer.urllib.request.urlopen")
    def test_custom_webhook_success(self, mock_urlopen):
        """Custom webhook passes full alert payload."""
        from scripts.alert_consumer import _send_custom_webhook

        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock())
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        alert = {"entity_name": "TestCorp", "composite_score": 85.0}
        status, error = _send_custom_webhook("https://example.com/webhook", alert)
        self.assertEqual(status, "sent")


class TestEmailDispatch(unittest.TestCase):
    """Test email dispatch."""

    def test_email_skipped_when_no_smtp(self):
        """Email is skipped when SMTP host is missing."""
        from scripts.alert_consumer import _send_email

        config = {"smtp_host": None, "to_addresses": []}
        alert = {"entity_name": "TestCorp", "composite_score": 85.0}
        status, error = _send_email(config, alert)
        self.assertEqual(status, "skipped")

    @patch("smtplib.SMTP")
    def test_email_sent_successfully(self, mock_smtp_cls):
        """Email returns sent on successful SMTP delivery."""
        from scripts.alert_consumer import _send_email

        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server
        config = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_user": "test@test.com",
            "smtp_password": "pass",
            "from_address": "test@test.com",
            "to_addresses": ["user@test.com"],
        }
        alert = {"entity_name": "TestCorp", "composite_score": 88.0}
        status, error = _send_email(config, alert)
        self.assertEqual(status, "sent")
        self.assertIsNone(error)
        mock_server.sendmail.assert_called_once()

    @patch("smtplib.SMTP")
    def test_email_failure(self, mock_smtp_cls):
        """Email returns failed on SMTP error."""
        from scripts.alert_consumer import _send_email

        mock_smtp_cls.side_effect = Exception("SMTP connection failed")
        config = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "to_addresses": ["user@test.com"],
        }
        alert = {"entity_name": "TestCorp", "composite_score": 88.0}
        status, error = _send_email(config, alert)
        self.assertEqual(status, "failed")
        self.assertIn("SMTP", error)


class TestDispatchAlert(unittest.TestCase):
    """Test the main dispatch_alert function."""

    def test_alert_filtered_below_threshold(self):
        """Alert below min_score_threshold is filtered."""
        from scripts.alert_consumer import dispatch_alert

        alert = {"entity_name": "TestCorp", "composite_score": 50.0}
        config = {}
        prefs = {"min_score_threshold": 80.0}
        result = dispatch_alert(alert, config, prefs, MagicMock())
        self.assertEqual(result["status"], "filtered")

    @patch("scripts.alert_consumer._is_quiet_hours", return_value=True)
    def test_alert_deferred_in_quiet_hours(self, mock_quiet):
        """Alert is deferred during quiet hours."""
        from scripts.alert_consumer import dispatch_alert

        alert = {"entity_name": "TestCorp", "composite_score": 90.0}
        config = {}
        prefs = {
            "min_score_threshold": 80.0,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        }
        result = dispatch_alert(alert, config, prefs, MagicMock())
        self.assertEqual(result["status"], "deferred")

    def test_alert_no_channels_configured(self):
        """Alert returns no_channels when nothing is enabled."""
        from scripts.alert_consumer import dispatch_alert

        alert = {"entity_name": "TestCorp", "composite_score": 90.0}
        config = {"channels": {}}
        prefs = {
            "email_enabled": True,
            "slack_enabled": True,
            "discord_enabled": True,
            "webhook_enabled": True,
            "min_score_threshold": 80.0,
        }
        result = dispatch_alert(alert, config, prefs, MagicMock())
        self.assertEqual(result["status"], "no_channels")

    @patch("scripts.alert_consumer._send_slack")
    def test_alert_dispatched_to_slack(self, mock_slack):
        """Alert dispatched to Slack channel."""
        from scripts.alert_consumer import dispatch_alert

        mock_slack.return_value = ("sent", None)
        alert = {"entity_name": "TestCorp", "composite_score": 90.0, "attribution": []}
        config = {
            "channels": {
                "webhook_slack": {
                    "enabled": True,
                    "url": "https://hooks.slack.com/test",
                },
            },
        }
        prefs = {
            "email_enabled": False,
            "slack_enabled": True,
            "discord_enabled": False,
            "webhook_enabled": False,
            "min_score_threshold": 80.0,
        }
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        result = dispatch_alert(alert, config, prefs, mock_conn)
        self.assertEqual(result["status"], "dispatched")
        self.assertEqual(result["channels"]["slack"]["status"], "sent")

    @patch("scripts.alert_consumer._send_email")
    def test_alert_failed_all_channels(self, mock_email):
        """Alert marked failed when all channels fail."""
        from scripts.alert_consumer import dispatch_alert

        mock_email.return_value = ("failed", "SMTP error")
        alert = {"entity_name": "TestCorp", "composite_score": 90.0, "attribution": []}
        config = {
            "channels": {
                "email": {
                    "enabled": True,
                    "smtp_host": "smtp.test.com",
                    "to_addresses": ["a@b.com"],
                },
            },
        }
        prefs = {
            "email_enabled": True,
            "slack_enabled": False,
            "discord_enabled": False,
            "webhook_enabled": False,
            "min_score_threshold": 80.0,
        }
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        result = dispatch_alert(alert, config, prefs, mock_conn)
        self.assertEqual(result["status"], "failed")


class TestDeadLetterQueue(unittest.TestCase):
    """Test dead letter queue functionality."""

    def test_move_to_dlq(self):
        """Alert is moved to dead letter queue on failure."""
        from scripts.alert_consumer import _move_to_dlq

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        alert = {
            "alert_type": "high_value_opportunity",
            "entity_name": "TestCorp",
            "entity_type": "company",
            "composite_score": 85.0,
        }
        _move_to_dlq(mock_conn, alert, "All channels failed", 1)

        # Should have called execute for CREATE TABLE and INSERT
        self.assertGreaterEqual(mock_cursor.execute.call_count, 2)

    def test_move_to_dlq_handles_db_error(self):
        """DLQ move doesn't crash on DB error."""
        from scripts.alert_consumer import _move_to_dlq

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn.cursor.return_value = mock_cursor
        # Should not raise
        _move_to_dlq(mock_conn, {"entity_name": "X"}, "error", 1)

    def test_retry_dlq_alerts(self):
        """DLQ retry re-attempts failed alerts."""
        from scripts.alert_consumer import _retry_dlq_alerts

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "alert_payload": '{"entity_name": "Test", "composite_score": 90}',
                "attempts": 1,
                "error_message": "failed",
            },
        ]
        mock_conn.cursor.return_value = mock_cursor

        with patch(
            "scripts.alert_consumer.dispatch_alert",
            return_value={"status": "dispatched"},
        ):
            _retry_dlq_alerts(mock_conn, {}, {}, max_retries=3)
            # Should delete the recovered alert
            delete_calls = [
                c for c in mock_cursor.execute.call_args_list if "DELETE" in str(c)
            ]
            self.assertGreater(len(delete_calls), 0)


class TestShutdownEvent(unittest.TestCase):
    """Test shutdown event."""

    def test_shutdown_event_exists(self):
        """Global shutdown event exists and is not set."""
        from scripts.alert_consumer import _shutdown

        self.assertFalse(_shutdown.is_set())


class TestAlertPreferencesSchema(unittest.TestCase):
    """Test alert_preferences table in schema."""

    def test_alert_preferences_in_schema(self):
        """alert_preferences table is defined in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        content = schema_path.read_text()
        self.assertIn("alert_preferences", content)
        self.assertIn("min_score_threshold", content)
        self.assertIn("quiet_hours_start", content)
        self.assertIn("max_alerts_per_hour", content)

    def test_alert_dead_letters_in_consumer(self):
        """alert_dead_letters table is created by the consumer."""
        consumer_path = Path(__file__).parent.parent / "scripts" / "alert_consumer.py"
        content = consumer_path.read_text()
        self.assertIn("alert_dead_letters", content)
        self.assertIn("_move_to_dlq", content)
        self.assertIn("_retry_dlq_alerts", content)


class TestPostWebhook(unittest.TestCase):
    """Test generic webhook POST."""

    @patch("scripts.alert_consumer.urllib.request.urlopen")
    def test_post_webhook_success(self, mock_urlopen):
        """Webhook POST succeeds with valid URL."""
        from scripts.alert_consumer import _post_webhook

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        status, error = _post_webhook("https://example.com/hook", {"test": True})
        self.assertEqual(status, "sent")
        self.assertIsNone(error)

    @patch("scripts.alert_consumer.urllib.request.urlopen")
    def test_post_webhook_failure(self, mock_urlopen):
        """Webhook POST returns failed on error."""
        from scripts.alert_consumer import _post_webhook

        mock_urlopen.side_effect = Exception("timeout")
        status, error = _post_webhook("https://example.com/hook", {"test": True})
        self.assertEqual(status, "failed")
        self.assertEqual(error, "timeout")


if __name__ == "__main__":
    unittest.main()
