"""Tests for agents/competitive_landscape_agent.py — competitive landscape analysis."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCompetitiveLandscapeAgent:
    """Test CompetitiveLandscapeAgent class."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    @pytest.fixture
    def agent(self):
        """Create a CompetitiveLandscapeAgent instance."""
        from agents.competitive_landscape_agent import CompetitiveLandscapeAgent
        return CompetitiveLandscapeAgent(config={}, dry_run=False)

    def test_agent_name(self, agent):
        """Test agent name property."""
        assert agent.name == "competitive_landscape"

    def test_agent_enabled_by_default(self, agent):
        """Test agent is enabled by default."""
        assert agent.enabled is True

    def test_execute_with_sector_data(self, agent, mock_connection):
        """Test execute with sector competitor data."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "SaaS",
                "competitor_count": 45,
                "avg_funding": 15_000_000,
                "well_funded_count": 20
            }
        ]

        top_cursor = MagicMock()
        top_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,  # sector query
            top_cursor,     # top competitors
            sector_cursor,  # insert/delete
            sector_cursor   # final
        ]

        with patch("agents.competitive_landscape_agent.get_connection", return_value=mock_connection):
            with patch("agents.competitive_landscape_agent.schema") as mock_schema:
                result = agent.execute()

        assert result.status == "success"
        assert result.data["sectors_analyzed"] == 1

    def test_market_concentration_calculation(self, agent, mock_connection):
        """Test market concentration is calculated correctly."""
        # Fragmented market (50+ competitors)
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {"sector": "SaaS", "competitor_count": 60, "avg_funding": 10_000_000, "well_funded_count": 30}
        ]

        top_cursor = MagicMock()
        top_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            top_cursor,
            sector_cursor,
            sector_cursor
        ]

        with patch("agents.competitive_landscape_agent.get_connection", return_value=mock_connection):
            with patch("agents.competitive_landscape_agent.schema"):
                result = agent.execute()

        assert result.status == "success"

    def test_entry_barriers_high(self, agent, mock_connection):
        """Test high entry barriers for hard sectors."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {"sector": "Semiconductors", "competitor_count": 15, "avg_funding": 50_000_000, "well_funded_count": 10}
        ]

        top_cursor = MagicMock()
        top_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            top_cursor,
            sector_cursor,
            sector_cursor
        ]

        with patch("agents.competitive_landscape_agent.get_connection", return_value=mock_connection):
            with patch("agents.competitive_landscape_agent.schema"):
                result = agent.execute()

        assert result.status == "success"

    def test_rivalry_intensity_high(self, agent, mock_connection):
        """Test high rivalry with many competitors and funding."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {"sector": "Fintech", "competitor_count": 55, "avg_funding": 20_000_000, "well_funded_count": 25}
        ]

        top_cursor = MagicMock()
        top_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            top_cursor,
            sector_cursor,
            sector_cursor
        ]

        with patch("agents.competitive_landscape_agent.get_connection", return_value=mock_connection):
            with patch("agents.competitive_landscape_agent.schema"):
                result = agent.execute()

        assert result.status == "success"

    def test_handles_empty_data(self, agent, mock_connection):
        """Test handling of empty data."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            sector_cursor
        ]

        with patch("agents.competitive_landscape_agent.get_connection", return_value=mock_connection):
            with patch("agents.competitive_landscape_agent.schema"):
                result = agent.execute()

        assert result.status == "success"
        assert result.data["sectors_analyzed"] == 0

    def test_database_operations(self, agent, mock_connection):
        """Test database insert and commit are called."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {"sector": "AI", "competitor_count": 30, "avg_funding": 12_000_000, "well_funded_count": 15}
        ]

        top_cursor = MagicMock()
        top_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            top_cursor,
            sector_cursor,
            sector_cursor
        ]

        with patch("agents.competitive_landscape_agent.get_connection", return_value=mock_connection):
            with patch("agents.competitive_landscape_agent.schema"):
                result = agent.execute()

        sector_cursor.execute.assert_any_call("DELETE FROM analysis_competitive_landscape")
        mock_connection.commit.assert_called()
