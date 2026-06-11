"""Tests for cost tracking agent."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCostTrackingAgent(unittest.TestCase):
    """Test cost tracking agent."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.cost_tracking_agent import CostTrackingAgent

        agent = CostTrackingAgent()
        self.assertEqual(agent.name, "cost_tracking")


if __name__ == "__main__":
    unittest.main()
