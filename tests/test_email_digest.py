"""Tests for email digest agent."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEmailDigestAgent(unittest.TestCase):
    """Test email digest agent."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.email_digest_agent import EmailDigestAgent
        agent = EmailDigestAgent()
        self.assertEqual(agent.name, "email_digest")


if __name__ == "__main__":
    unittest.main()
