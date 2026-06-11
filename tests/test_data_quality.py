"""Tests for data quality agent."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataQualityAgent(unittest.TestCase):
    """Test data quality agent."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.data_quality_agent import DataQualityAgent

        agent = DataQualityAgent()
        self.assertEqual(agent.name, "data_quality")


if __name__ == "__main__":
    unittest.main()
