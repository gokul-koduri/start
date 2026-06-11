"""Tests for agents/technology_stack_agent.py — technology stack analysis."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTechnologyStackAgent:
    """Test TechnologyStackAgent class."""

    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    @pytest.fixture
    def agent(self):
        from agents.technology_stack_agent import TechnologyStackAgent

        return TechnologyStackAgent(config={}, dry_run=False)

    def test_agent_name(self, agent):
        assert agent.name == "technology_stack"

    def test_execute_with_github_data(self, agent, mock_connection):
        gh_cursor = MagicMock()
        gh_cursor.fetchall.return_value = [
            {"language": "Python", "repo_count": 100, "avg_velocity": 50}
        ]

        so_cursor = MagicMock()
        so_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            gh_cursor,
            so_cursor,
            gh_cursor,
            gh_cursor,
        ]

        with patch(
            "agents.technology_stack_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.technology_stack_agent.schema"):
                result = agent.execute()

        assert result.status == "success"

    def test_handles_empty_data(self, agent, mock_connection):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        mock_connection.cursor.side_effect = [cursor, cursor, cursor, cursor]

        with patch(
            "agents.technology_stack_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.technology_stack_agent.schema"):
                result = agent.execute()

        assert result.status == "success"
