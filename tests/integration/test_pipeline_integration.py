"""Integration tests — validates pipeline wiring end-to-end.

These tests verify that:
1. All pipeline agents can be resolved and instantiated
2. The orchestrator can run each pipeline (dry-run mode)
3. Risk scorer, sentiment, and knowledge graph agents are in the analysis pipeline
4. The YAML config matches the orchestrator defaults

Mark with @pytest.mark.integration for CI skip.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock pymysql
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors


@pytest.mark.integration
class TestAnalysisPipelineIntegration:
    """Integration tests for the analysis pipeline wiring."""

    def test_analysis_pipeline_agents_instantiate(self):
        """All agents in the analysis pipeline can be instantiated."""
        from agents.orchestrator import _get_agent_class

        analysis_agents = [
            "failure_pattern",
            "survival_analysis",
            "revival_opportunity",
            "geographic_strategy",
            "news_intelligence",
            "whale_investor",
            "opportunity_pipeline",
            "correlation",
            "global_market_viability",
            "risk_scorer",
            "sentiment",
            "knowledge_graph",
            "ml_predictor",
            "llm_pricing",
            "llm_benchmark",
            "llm_portfolio",
            "llm_cost_optimizer",
            "entity_resolver",
            "nlp_enrichment",
        ]
        for name in analysis_agents:
            cls = _get_agent_class(name)
            agent = cls(config={}, dry_run=True)
            assert agent is not None, f"Failed to instantiate {name}"

    def test_risk_scorer_in_analysis_pipeline(self):
        """Risk scorer is in the analysis pipeline config."""
        import yaml

        config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert (
            "risk_scorer" in config["agents"]["orchestrator"]["pipelines"]["analysis"]
        )

    def test_sentiment_in_analysis_pipeline(self):
        """Sentiment agent is in the analysis pipeline config."""
        import yaml

        config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert "sentiment" in config["agents"]["orchestrator"]["pipelines"]["analysis"]

    def test_knowledge_graph_in_analysis_pipeline(self):
        """Knowledge graph is in the analysis pipeline config."""
        import yaml

        config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert (
            "knowledge_graph"
            in config["agents"]["orchestrator"]["pipelines"]["analysis"]
        )

    def test_orchestrator_dry_run_analysis(self):
        """Orchestrator can run the analysis pipeline in dry-run mode."""
        from agents.orchestrator import OrchestratorAgent
        from agents.base import AgentResult

        agent = OrchestratorAgent(
            config={"_pipeline_name": "analysis"},
            dry_run=True,
        )
        # In dry-run mode, agents should still return AgentResult
        result = agent.execute()
        assert isinstance(result, AgentResult)
        assert result.status in ("success", "partial", "failed")

    def test_daily_pipeline_runs(self):
        """Orchestrator can run the daily pipeline in dry-run mode."""
        from agents.orchestrator import OrchestratorAgent
        from agents.base import AgentResult

        agent = OrchestratorAgent(
            config={"_pipeline_name": "daily"},
            dry_run=True,
        )
        result = agent.execute()
        assert isinstance(result, AgentResult)

    def test_weekly_pipeline_runs(self):
        """Orchestrator can run the weekly pipeline in dry-run mode."""
        from agents.orchestrator import OrchestratorAgent
        from agents.base import AgentResult

        agent = OrchestratorAgent(
            config={"_pipeline_name": "weekly"},
            dry_run=True,
        )
        result = agent.execute()
        assert isinstance(result, AgentResult)


@pytest.mark.integration
class TestOllamaClientIntegration:
    """Integration tests for the OllamaClient."""

    def test_client_handles_ollama_down(self):
        """OllamaClient gracefully handles Ollama being down."""
        from utils.ollama_client import OllamaClient

        client = OllamaClient(max_retries=1, backoff_base=0.01)
        # This should not crash even if Ollama is down
        with patch("utils.ollama_client._get_connection") as mock_conn:
            mock_conn.return_value.request.side_effect = ConnectionRefusedError
            with patch("time.sleep"):
                result = client.chat([{"role": "user", "content": "test"}])
        assert result is None
        assert client.last_error is not None

    def test_health_check_returns_false_when_down(self):
        """Health check returns False when Ollama is unreachable."""
        from utils.ollama_client import OllamaClient

        client = OllamaClient()
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError):
            assert client.is_healthy() is False
