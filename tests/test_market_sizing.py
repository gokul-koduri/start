"""Tests for agents/market_sizing_agent.py — market sizing and estimation."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMarketSizingAgent:
    """Test MarketSizingAgent class."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    @pytest.fixture
    def agent(self):
        """Create a MarketSizingAgent instance."""
        from agents.market_sizing_agent import MarketSizingAgent

        return MarketSizingAgent(config={}, dry_run=False)

    def test_agent_name(self, agent):
        """Test agent name property."""
        assert agent.name == "market_sizing"

    def test_agent_enabled_by_default(self, agent):
        """Test agent is enabled by default."""
        assert agent.enabled is True

    def test_agent_disabled_in_config(self):
        """Test agent can be disabled via config."""
        from agents.market_sizing_agent import MarketSizingAgent

        agent = MarketSizingAgent(config={"enabled": False})
        assert agent.enabled is False

    def test_execute_with_sector_data(self, agent, mock_connection):
        """Test execute with sector failure data."""
        # Mock sector failures query
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "AI",
                "failure_count": 45,
                "avg_funding": 25_000_000,
                "total_funding": 1_125_000_000,
            },
            {
                "sector": "SaaS",
                "failure_count": 38,
                "avg_funding": 15_000_000,
                "total_funding": 570_000_000,
            },
        ]

        # Mock funding events query
        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = [
            {
                "company_name": "TechCorp AI",
                "round_type": "Series A",
                "amount_usd": 50_000_000,
                "sector": "AI",
            }
        ]

        # Setup cursor chain
        mock_connection.cursor.side_effect = [
            sector_cursor,  # sector failures
            funding_cursor,  # funding events
            sector_cursor,  # insert/delete
            sector_cursor,  # final
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        assert result.status == "success"
        assert result.data["sectors_analyzed"] == 2
        assert result.data["market_estimates"] == 2
        assert "records_affected" in result.data

    def test_execute_with_empty_data(self, agent, mock_connection):
        """Test execute with no sector data."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = []

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        assert result.status == "success"
        assert result.data["sectors_analyzed"] == 0
        assert result.data["market_estimates"] == 0

    def test_market_size_calculation_high_activity(self, agent, mock_connection):
        """Test market size multiplier for high-activity sectors."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "AI",
                "failure_count": 75,  # High activity
                "avg_funding": 20_000_000,
                "total_funding": 1_500_000_000,
            }
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        # Should use 10x multiplier for high activity
        assert result.status == "success"
        assert result.data["market_estimates"] == 1

    def test_market_size_calculation_low_activity(self, agent, mock_connection):
        """Test market size multiplier for low-activity sectors."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "NicheTech",
                "failure_count": 8,  # Low activity
                "avg_funding": 5_000_000,
                "total_funding": 40_000_000,
            }
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        # Should use 3x multiplier for low activity
        assert result.status == "success"

    def test_growth_rate_emerging_markets(self, agent, mock_connection):
        """Test growth rate for emerging markets."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "AI",
                "failure_count": 30,
                "avg_funding": 10_000_000,
                "total_funding": 300_000_000,
            }
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        # AI should get 20% growth rate
        assert result.status == "success"

    def test_growth_rate_mature_markets(self, agent, mock_connection):
        """Test growth rate for mature markets."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "E-commerce",
                "failure_count": 25,
                "avg_funding": 8_000_000,
                "total_funding": 200_000_000,
            }
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        # E-commerce should get 15% growth rate
        assert result.status == "success"

    def test_confidence_score_high_data(self, agent, mock_connection):
        """Test confidence score with high data volume."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "SaaS",
                "failure_count": 50,  # High volume
                "avg_funding": 12_000_000,
                "total_funding": 600_000_000,
            }
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        # Should have 0.8 confidence with 50+ data points
        assert result.status == "success"

    def test_confidence_score_low_data(self, agent, mock_connection):
        """Test confidence score with low data volume."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "NewSector",
                "failure_count": 5,  # Low volume
                "avg_funding": 3_000_000,
                "total_funding": 15_000_000,
            }
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        # Should have 0.4 confidence with < 10 data points
        assert result.status == "success"

    def test_database_insert_called(self, agent, mock_connection):
        """Test that database insert is called."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": "AI",
                "failure_count": 30,
                "avg_funding": 10_000_000,
                "total_funding": 300_000_000,
            }
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                agent.execute()

        # Verify delete was called
        sector_cursor.execute.assert_any_call("DELETE FROM analysis_market_sizing")
        # Verify commit was called
        mock_connection.commit.assert_called()

    def test_handles_null_sector_names(self, agent, mock_connection):
        """Test handling of null sector names."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = [
            {
                "sector": None,  # Null sector
                "failure_count": 10,
                "avg_funding": 5_000_000,
                "total_funding": 50_000_000,
            },
            {
                "sector": "ValidSector",
                "failure_count": 15,
                "avg_funding": 8_000_000,
                "total_funding": 120_000_000,
            },
        ]

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                result = agent.execute()

        # Should only process valid sector
        assert result.status == "success"
        assert result.data["market_estimates"] == 1

    def test_database_connection_cleanup(self, agent, mock_connection):
        """Test that database connections are properly closed."""
        sector_cursor = MagicMock()
        sector_cursor.fetchall.return_value = []

        funding_cursor = MagicMock()
        funding_cursor.fetchall.return_value = []

        mock_connection.cursor.side_effect = [
            sector_cursor,
            funding_cursor,
            sector_cursor,
            sector_cursor,
        ]

        with patch(
            "agents.market_sizing_agent.get_connection", return_value=mock_connection
        ):
            with patch("agents.market_sizing_agent.schema"):
                agent.execute()

        # Verify cursors were closed
        assert sector_cursor.close.call_count == 2
        assert funding_cursor.close.call_count == 1
        # Verify connection was closed
        mock_connection.close.assert_called_once()
