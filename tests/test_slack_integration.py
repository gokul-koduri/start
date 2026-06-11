"""Tests for Slack integration agent."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSlackIntegrationAgent(unittest.TestCase):
    """Test Slack integration agent."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.slack_integration_agent import SlackIntegrationAgent

        agent = SlackIntegrationAgent({"webhook_url": "https://hooks.slack.com/test"})
        self.assertEqual(agent.name, "slack_integration")


if __name__ == "__main__":
    unittest.main()
