"""Tests for pipeline health agent."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPipelineHealthAgent(unittest.TestCase):
    """Test pipeline health agent."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.pipeline_health_agent import PipelineHealthAgent
        agent = PipelineHealthAgent()
        self.assertEqual(agent.name, "pipeline_health")


if __name__ == "__main__":
    unittest.main()
