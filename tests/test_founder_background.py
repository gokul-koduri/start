"""Tests for agents/founder_background_agent.py — founder background analysis."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFounderBackgroundAgent:
    """Test FounderBackgroundAgent class."""

    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    @pytest.fixture
    def agent(self):
        from agents.founder_background_agent import FounderBackgroundAgent

        return FounderBackgroundAgent(config={}, dry_run=False)

    def test_agent_name(self, agent):
        assert agent.name == "founder_background"

    def test_execute_with_data(self, agent, mock_connection):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "company_name": "TechCorp",
                "officers": '{"CEO": "John Doe", "CTO": "Jane Smith"}',
                "jurisdiction_code": "US",
                "incorporated": "2020-01-15",
            }
        ]

        mock_connection.cursor.side_effect = [cursor, cursor, cursor]

        with patch(
            "agents.founder_background_agent.get_connection",
            return_value=mock_connection,
        ):
            with patch("agents.founder_background_agent.schema"):
                result = agent.execute()

        assert result.status == "success"

    def test_handles_empty_data(self, agent, mock_connection):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [cursor, cursor, cursor]

        with patch(
            "agents.founder_background_agent.get_connection",
            return_value=mock_connection,
        ):
            with patch("agents.founder_background_agent.schema"):
                result = agent.execute()

        assert result.status == "success"
