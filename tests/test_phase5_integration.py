"""Phase 5 Integration Tests — verify all Phase 5 agents work together."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPhase5AgentsIntegration:
    """Integration tests for all Phase 5 Advanced Intelligence agents."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_all_phase5_agents_exist(self):
        """Test that all Phase 5 agents can be imported."""
        phase5_agents = [
            ("agents.market_sizing_agent", "MarketSizingAgent"),
            ("agents.competitive_landscape_agent", "CompetitiveLandscapeAgent"),
            ("agents.founder_background_agent", "FounderBackgroundAgent"),
            ("agents.technology_stack_agent", "TechnologyStackAgent"),
            ("agents.moat_analyzer_agent", "MoatAnalyzerAgent"),
            ("agents.timing_agent", "TimingAgent"),
            ("agents.graph_traversal_agent", "GraphTraversalAgent"),
            ("agents.community_detector_agent", "CommunityDetectorAgent"),
            ("agents.influence_propagation_agent", "InfluencePropagationAgent"),
            ("agents.temporal_graph_agent", "TemporalGraphAgent"),
            ("agents.topic_modeling_agent", "TopicModelingAgent"),
            ("agents.relationship_extractor_agent", "RelationshipExtractorAgent"),
            ("agents.trend_detector_agent", "TrendDetectorAgent"),
            ("agents.intent_classifier_agent", "IntentClassifierAgent"),
            ("agents.sector_rotation_agent", "SectorRotationAgent"),
            ("agents.cohort_analysis_agent", "CohortAnalysisAgent"),
        ]

        for module_name, class_name in phase5_agents:
            module = __import__(module_name, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            assert agent_class is not None
            # Verify it has the required methods
            assert hasattr(agent_class, "name")
            # Verify it's a property (not callable directly, but accessible)
            agent_instance = agent_class(config={}, dry_run=False)
            assert agent_instance.name is not None

    def test_orchestrator_has_all_phase5_agents(self):
        """Test that orchestrator can load all Phase 5 agents."""
        from agents.orchestrator import _get_agent_class

        phase5_agent_names = [
            "market_sizing",
            "competitive_landscape",
            "founder_background",
            "technology_stack",
            "moat_analyzer",
            "timing",
            "graph_traversal",
            "community_detector",
            "influence_propagation",
            "temporal_graph",
            "topic_modeling",
            "relationship_extractor",
            "trend_detector",
            "intent_classifier",
            "sector_rotation",
            "cohort_analysis",
        ]

        for agent_name in phase5_agent_names:
            try:
                agent_class = _get_agent_class(agent_name)
                assert agent_class is not None
            except ValueError as e:
                pytest.fail(f"Failed to load agent '{agent_name}': {e}")

    def test_all_phase5_agents_execute(self, mock_connection):
        """Test that all Phase 5 agents can execute successfully."""
        phase5_agents = [
            ("agents.market_sizing_agent", "MarketSizingAgent"),
            ("agents.competitive_landscape_agent", "CompetitiveLandscapeAgent"),
            ("agents.founder_background_agent", "FounderBackgroundAgent"),
            ("agents.technology_stack_agent", "TechnologyStackAgent"),
            ("agents.moat_analyzer_agent", "MoatAnalyzerAgent"),
            ("agents.timing_agent", "TimingAgent"),
            ("agents.graph_traversal_agent", "GraphTraversalAgent"),
            ("agents.community_detector_agent", "CommunityDetectorAgent"),
            ("agents.influence_propagation_agent", "InfluencePropagationAgent"),
            ("agents.temporal_graph_agent", "TemporalGraphAgent"),
            ("agents.topic_modeling_agent", "TopicModelingAgent"),
            ("agents.relationship_extractor_agent", "RelationshipExtractorAgent"),
            ("agents.trend_detector_agent", "TrendDetectorAgent"),
            ("agents.intent_classifier_agent", "IntentClassifierAgent"),
            ("agents.sector_rotation_agent", "SectorRotationAgent"),
            ("agents.cohort_analysis_agent", "CohortAnalysisAgent"),
        ]

        for module_name, class_name in phase5_agents:
            module = __import__(module_name, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            agent = agent_class(config={}, dry_run=False)

            # Setup mock
            cursor = MagicMock()
            cursor.fetchall.return_value = []
            mock_connection.cursor.side_effect = [cursor, cursor, cursor]

            with patch(f"{module_name}.get_connection", return_value=mock_connection):
                with patch(f"{module_name}.schema"):
                    result = agent.execute()

            assert result.status == "success"
            assert result.agent_name == agent.name

    def test_schema_version_is_15(self):
        """Test that schema version has been bumped to 15 or later."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        # Allow version 15, 16, or 17 (Phase 6 and Sprint 1 bumped it)
        assert "_SCHEMA_VERSION = 15" in schema_content or "_SCHEMA_VERSION = 16" in schema_content or "_SCHEMA_VERSION = 17" in schema_content or "_SCHEMA_VERSION = 18" in schema_content or "_SCHEMA_VERSION = 19" in schema_content or "_SCHEMA_VERSION = 20" in schema_content

    def test_all_analysis_tables_exist(self):
        """Test that all Phase 5 analysis tables exist in schema file."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()

        analysis_tables = [
            "analysis_market_sizing",
            "analysis_competitive_landscape",
            "analysis_founder_background",
            "analysis_technology_stack",
            "analysis_moat",
            "analysis_timing",
            "analysis_graph_traversal",
            "analysis_community_detection",
            "analysis_influence_propagation",
            "analysis_temporal_graph",
            "analysis_topic_modeling",
            "analysis_relationship_extraction",
            "analysis_trend_detection",
            "analysis_intent_classification",
            "analysis_sector_rotation",
            "analysis_cohort_analysis",
        ]
        for table in analysis_tables:
            assert table in schema_content, f"Missing table: {table}"

    def test_phase5_agent_count(self):
        """Test that we have exactly 16 Phase 5 agents."""
        from agents.orchestrator import AGENT_REGISTRY

        phase5_agents = [
            "market_sizing",
            "competitive_landscape",
            "founder_background",
            "technology_stack",
            "moat_analyzer",
            "timing",
            "graph_traversal",
            "community_detector",
            "influence_propagation",
            "temporal_graph",
            "topic_modeling",
            "relationship_extractor",
            "trend_detector",
            "intent_classifier",
            "sector_rotation",
            "cohort_analysis",
        ]

        # Count how many are registered
        registered_count = sum(1 for name in phase5_agents if name in AGENT_REGISTRY)
        assert registered_count == 16, f"Expected 16 Phase 5 agents, found {registered_count}"
