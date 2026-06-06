"""Tests for feed generator agent."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFeedGeneratorAgent(unittest.TestCase):
    """Test feed generator agent."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.feed_generator_agent import FeedGeneratorAgent
        agent = FeedGeneratorAgent()
        self.assertEqual(agent.name, "feed_generator")


if __name__ == "__main__":
    unittest.main()
