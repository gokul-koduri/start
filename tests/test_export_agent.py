"""Tests for export agent."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestExportAgent(unittest.TestCase):
    """Test export agent."""

    def test_agent_exists(self):
        """Test agent can be imported."""
        from agents.export_agent import ExportAgent
        agent = ExportAgent()
        self.assertEqual(agent.name, "export")


if __name__ == "__main__":
    unittest.main()
