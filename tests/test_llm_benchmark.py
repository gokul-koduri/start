"""Tests for llm_benchmark_agent."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pymysql
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

from agents.llm_benchmark_agent import LLMBenchmarkAgent  # noqa: E402


class TestLLMBenchmarkAgent:
    """Tests for LLMBenchmarkAgent — instantiation and execute."""

    def test_instantiation(self):
        """Agent can be instantiated with default config."""
        agent = LLMBenchmarkAgent(config={}, dry_run=True)
        assert agent is not None

    def test_has_name_property(self):
        """Agent has a name property."""
        agent = LLMBenchmarkAgent(config={}, dry_run=True)
        assert hasattr(agent, "name")
        assert isinstance(agent.name, str)

    def test_execute_returns_result(self):
        """Execute returns an AgentResult."""
        from agents.base import AgentResult

        agent = LLMBenchmarkAgent(config={}, dry_run=True)
        result = agent.execute()
        assert isinstance(result, AgentResult)
        assert result.status in ("success", "partial", "failed", "skipped")
