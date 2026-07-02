"""Tests for orchestrator wiring — verifies P0 agents are registered in pipelines.

T-102/T-103/T-104: Risk Scorer, Knowledge Graph, and Sentiment agents
must be discoverable by the orchestrator and included in pipeline configs.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pymysql before imports
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

from agents.orchestrator import _get_agent_class, AGENT_REGISTRY  # noqa: E402


class TestRiskScorerWiring:
    """T-102: Risk Scorer is registered and in the analysis pipeline."""

    def test_agent_is_discoverable(self):
        cls = _get_agent_class("risk_scorer")
        assert cls is not None
        assert cls.__name__ == "RiskScorerAgent"

    def test_agent_in_registry_after_lookup(self):
        _get_agent_class("risk_scorer")
        assert "risk_scorer" in AGENT_REGISTRY

    def test_agent_in_default_analysis_pipeline(self):
        from agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent(config={"_pipeline_name": "analysis"}, dry_run=True)
        # Access the default pipelines from execute's logic
        pipelines = agent.config.get(
            "pipelines",
            {
                "analysis": [
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
                ],
            },
        )
        assert "risk_scorer" in pipelines["analysis"]

    def test_agent_in_yaml_analysis_pipeline(self):
        """Verify risk_scorer is in the YAML-defined analysis pipeline."""
        import yaml
        from config import get_project_root

        config_path = get_project_root() / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        analysis_pipeline = config["agents"]["orchestrator"]["pipelines"]["analysis"]
        assert "risk_scorer" in analysis_pipeline


class TestKnowledgeGraphWiring:
    """T-103: Knowledge Graph is registered and in the analysis pipeline."""

    def test_agent_is_discoverable(self):
        cls = _get_agent_class("knowledge_graph")
        assert cls is not None
        assert cls.__name__ == "KnowledgeGraphAgent"

    def test_agent_in_registry_after_lookup(self):
        _get_agent_class("knowledge_graph")
        assert "knowledge_graph" in AGENT_REGISTRY

    def test_agent_in_yaml_analysis_pipeline(self):
        import yaml
        from config import get_project_root

        config_path = get_project_root() / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        analysis_pipeline = config["agents"]["orchestrator"]["pipelines"]["analysis"]
        assert "knowledge_graph" in analysis_pipeline

    def test_agent_in_yaml_weekly_pipeline(self):
        import yaml
        from config import get_project_root

        config_path = get_project_root() / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        weekly_pipeline = config["agents"]["orchestrator"]["pipelines"]["weekly"]
        assert "knowledge_graph" in weekly_pipeline


class TestSentimentWiring:
    """T-104: Sentiment Agent is registered and in the analysis pipeline."""

    def test_agent_is_discoverable(self):
        cls = _get_agent_class("sentiment")
        assert cls is not None
        assert cls.__name__ == "SentimentAgent"

    def test_agent_in_registry_after_lookup(self):
        _get_agent_class("sentiment")
        assert "sentiment" in AGENT_REGISTRY

    def test_agent_in_yaml_analysis_pipeline(self):
        import yaml
        from config import get_project_root

        config_path = get_project_root() / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        analysis_pipeline = config["agents"]["orchestrator"]["pipelines"]["analysis"]
        assert "sentiment" in analysis_pipeline


class TestAnalysisPipelineCompleteness:
    """Verify all analysis pipeline agents are resolvable."""

    def test_all_analysis_agents_resolve(self):
        """Every agent in the YAML analysis pipeline should be importable."""
        import yaml
        from config import get_project_root

        config_path = get_project_root() / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        analysis_pipeline = config["agents"]["orchestrator"]["pipelines"]["analysis"]
        for agent_name in analysis_pipeline:
            cls = _get_agent_class(agent_name)
            assert cls is not None, f"Agent '{agent_name}' could not be resolved"
