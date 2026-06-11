"""Tests for webhook dispatcher."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWebhookDispatcher(unittest.TestCase):
    """Test webhook dispatcher."""

    def setUp(self):
        """Set up test fixtures."""
        from webhooks.dispatcher import WebhookDispatcher

        self.dispatcher = WebhookDispatcher()

    def test_register_webhook(self):
        """Test webhook registration."""
        self.dispatcher.register("test_event", "https://example.com/webhook")
        self.assertIn("test_event", self.dispatcher.webhooks)
        self.assertEqual(len(self.dispatcher.webhooks["test_event"]), 1)

    def test_dispatch_event(self):
        """Test event dispatching."""
        self.dispatcher.register("test_event", "https://example.com/webhook")
        result = self.dispatcher.dispatch("test_event", {"test": "data"})
        self.assertEqual(result["event_type"], "test_event")
        self.assertEqual(result["registered"], 1)


if __name__ == "__main__":
    unittest.main()
