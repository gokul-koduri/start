"""Tests for agents/topic_modeling_agent.py"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTopicModelingAgent:
    """Test TopicModelingAgent class."""

    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    @pytest.fixture
    def agent(self):
        from agents.topic_modeling_agent import TopicModelingAgent

        return TopicModelingAgent(config={}, dry_run=False)

    def test_agent_name(self, agent):
        assert agent.name == "topic_modeling"

    def test_execute_with_data(self, agent, mock_connection):
        cursor = MagicMock()
        cursor.fetchall.return_value = [{"sector": "AI", "count": 10}]
        mock_connection.cursor.side_effect = [cursor, cursor, cursor]

        with patch(
            "agents.topic_modeling_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.topic_modeling_agent.schema"):
                result = agent.execute()

        assert result.status == "success"

    def test_handles_empty_data(self, agent, mock_connection):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        mock_connection.cursor.side_effect = [cursor, cursor, cursor]

        with patch(
            "agents.topic_modeling_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.topic_modeling_agent.schema"):
                result = agent.execute()

        assert result.status == "success"
