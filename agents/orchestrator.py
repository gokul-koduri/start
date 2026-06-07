"""Orchestrator agent — composes and runs the full agent pipeline."""

import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from agents.collection_agent import CollectionAgent
from agents.report_agent import ReportAgent

_logger = logging.getLogger(__name__)

# Agent registry — maps string names to agent classes
AGENT_REGISTRY = {
    "collection": CollectionAgent,
    "report": ReportAgent,
    # These are added dynamically to avoid import errors before they're created
}

# Lazy imports for agents with optional dependencies
def _get_agent_class(name: str):
    """Get agent class by name, with lazy imports for optional agents."""
    if name in AGENT_REGISTRY:
        return AGENT_REGISTRY[name]

    # Lazy imports for agents that may have optional deps
    if name == "dashboard":
        from agents.dashboard_agent import DashboardAgent
        AGENT_REGISTRY["dashboard"] = DashboardAgent
        return DashboardAgent
    elif name == "git_publisher":
        from agents.git_publisher_agent import GitPublisherAgent
        AGENT_REGISTRY["git_publisher"] = GitPublisherAgent
        return GitPublisherAgent
    elif name == "internet_research":
        from agents.internet_research_agent import InternetResearchAgent
        AGENT_REGISTRY["internet_research"] = InternetResearchAgent
        return InternetResearchAgent
    elif name == "failure_pattern":
        from agents.failure_pattern_agent import FailurePatternAgent
        AGENT_REGISTRY["failure_pattern"] = FailurePatternAgent
        return FailurePatternAgent
    elif name == "survival_analysis":
        from agents.survival_analysis_agent import SurvivalAnalysisAgent
        AGENT_REGISTRY["survival_analysis"] = SurvivalAnalysisAgent
        return SurvivalAnalysisAgent
    elif name == "revival_opportunity":
        from agents.revival_opportunity_agent import RevivalOpportunityAgent
        AGENT_REGISTRY["revival_opportunity"] = RevivalOpportunityAgent
        return RevivalOpportunityAgent
    elif name == "geographic_strategy":
        from agents.geographic_strategy_agent import GeographicStrategyAgent
        AGENT_REGISTRY["geographic_strategy"] = GeographicStrategyAgent
        return GeographicStrategyAgent
    elif name == "news_intelligence":
        from agents.news_intelligence_agent import NewsIntelligenceAgent
        AGENT_REGISTRY["news_intelligence"] = NewsIntelligenceAgent
        return NewsIntelligenceAgent
    elif name == "opportunity_pipeline":
        from agents.opportunity_pipeline_agent import OpportunityPipelineAgent
        AGENT_REGISTRY["opportunity_pipeline"] = OpportunityPipelineAgent
        return OpportunityPipelineAgent
    elif name == "whale_investor":
        from agents.whale_investor_agent import WhaleInvestorAgent
        AGENT_REGISTRY["whale_investor"] = WhaleInvestorAgent
        return WhaleInvestorAgent
    elif name == "correlation":
        from agents.correlation_agent import CorrelationAgent
        AGENT_REGISTRY["correlation"] = CorrelationAgent
        return CorrelationAgent
    elif name == "global_market_viability":
        from agents.global_market_viability_agent import GlobalMarketViabilityAgent
        AGENT_REGISTRY["global_market_viability"] = GlobalMarketViabilityAgent
        return GlobalMarketViabilityAgent
    elif name == "llm_pricing":
        from agents.llm_pricing_agent import LLMPricingAgent
        AGENT_REGISTRY["llm_pricing"] = LLMPricingAgent
        return LLMPricingAgent
    elif name == "llm_benchmark":
        from agents.llm_benchmark_agent import LLMBenchmarkAgent
        AGENT_REGISTRY["llm_benchmark"] = LLMBenchmarkAgent
        return LLMBenchmarkAgent
    elif name == "llm_portfolio":
        from agents.llm_portfolio_agent import LLMPortfolioAgent
        AGENT_REGISTRY["llm_portfolio"] = LLMPortfolioAgent
        return LLMPortfolioAgent
    elif name == "llm_cost_optimizer":
        from agents.llm_cost_optimizer_agent import LLMCostOptimizerAgent
        AGENT_REGISTRY["llm_cost_optimizer"] = LLMCostOptimizerAgent
        return LLMCostOptimizerAgent
    elif name == "license_manager":
        from agents.license_agent import LicenseAgent
        AGENT_REGISTRY["license_manager"] = LicenseAgent
        return LicenseAgent
    elif name == "knowledge_graph":
        from agents.knowledge_graph_agent import KnowledgeGraphAgent
        AGENT_REGISTRY["knowledge_graph"] = KnowledgeGraphAgent
        return KnowledgeGraphAgent
    elif name == "ai_analyst":
        from agents.ai_analyst_agent import AIAnalystAgent
        AGENT_REGISTRY["ai_analyst"] = AIAnalystAgent
        return AIAnalystAgent
    elif name == "alert_dispatcher":
        from agents.alert_dispatcher_agent import AlertDispatcherAgent
        AGENT_REGISTRY["alert_dispatcher"] = AlertDispatcherAgent
        return AlertDispatcherAgent
    elif name == "report_generator":
        from agents.report_generator_agent import ReportGeneratorAgent
        AGENT_REGISTRY["report_generator"] = ReportGeneratorAgent
        return ReportGeneratorAgent
    elif name == "stripe_payments":
        from agents.stripe_webhook_agent import StripePaymentAgent
        AGENT_REGISTRY["stripe_payments"] = StripePaymentAgent
        return StripePaymentAgent
    elif name == "span_monitor":
        from agents.span_agent import SpanAgent
        AGENT_REGISTRY["span_monitor"] = SpanAgent
        return SpanAgent
    elif name == "risk_scorer":
        from agents.risk_scorer_agent import RiskScorerAgent
        AGENT_REGISTRY["risk_scorer"] = RiskScorerAgent
        return RiskScorerAgent
    elif name == "ml_predictor":
        from agents.ml_predictor_agent import MLPredictorAgent
        AGENT_REGISTRY["ml_predictor"] = MLPredictorAgent
        return MLPredictorAgent
    elif name == "sentiment":
        from agents.sentiment_agent import SentimentAgent
        AGENT_REGISTRY["sentiment"] = SentimentAgent
        return SentimentAgent
    elif name == "opportunity_scorer":
        from agents.opportunity_scorer_agent import OpportunityScorerAgent
        AGENT_REGISTRY["opportunity_scorer"] = OpportunityScorerAgent
        return OpportunityScorerAgent
    elif name == "entity_resolver":
        from agents.entity_resolver_agent import EntityResolverAgent
        AGENT_REGISTRY["entity_resolver"] = EntityResolverAgent
        return EntityResolverAgent
    elif name == "nlp_enrichment":
        from agents.nlp_enrichment_agent import NLPEnrichmentAgent
        AGENT_REGISTRY["nlp_enrichment"] = NLPEnrichmentAgent
        return NLPEnrichmentAgent
    elif name == "semantic_search":
        from agents.semantic_search_agent import SemanticSearchAgent
        AGENT_REGISTRY["semantic_search"] = SemanticSearchAgent
        return SemanticSearchAgent
    elif name == "project_monitor":
        from agents.project_monitor_agent import ProjectMonitorAgent
        AGENT_REGISTRY["project_monitor"] = ProjectMonitorAgent
        return ProjectMonitorAgent
    elif name == "market_sizing":
        from agents.market_sizing_agent import MarketSizingAgent
        AGENT_REGISTRY["market_sizing"] = MarketSizingAgent
        return MarketSizingAgent
    elif name == "competitive_landscape":
        from agents.competitive_landscape_agent import CompetitiveLandscapeAgent
        AGENT_REGISTRY["competitive_landscape"] = CompetitiveLandscapeAgent
        return CompetitiveLandscapeAgent
    elif name == "founder_background":
        from agents.founder_background_agent import FounderBackgroundAgent
        AGENT_REGISTRY["founder_background"] = FounderBackgroundAgent
        return FounderBackgroundAgent
    elif name == "technology_stack":
        from agents.technology_stack_agent import TechnologyStackAgent
        AGENT_REGISTRY["technology_stack"] = TechnologyStackAgent
        return TechnologyStackAgent
    elif name == "moat_analyzer":
        from agents.moat_analyzer_agent import MoatAnalyzerAgent
        AGENT_REGISTRY["moat_analyzer"] = MoatAnalyzerAgent
        return MoatAnalyzerAgent
    elif name == "timing":
        from agents.timing_agent import TimingAgent
        AGENT_REGISTRY["timing"] = TimingAgent
        return TimingAgent
    elif name == "graph_traversal":
        from agents.graph_traversal_agent import GraphTraversalAgent
        AGENT_REGISTRY["graph_traversal"] = GraphTraversalAgent
        return GraphTraversalAgent
    elif name == "community_detector":
        from agents.community_detector_agent import CommunityDetectorAgent
        AGENT_REGISTRY["community_detector"] = CommunityDetectorAgent
        return CommunityDetectorAgent
    elif name == "influence_propagation":
        from agents.influence_propagation_agent import InfluencePropagationAgent
        AGENT_REGISTRY["influence_propagation"] = InfluencePropagationAgent
        return InfluencePropagationAgent
    elif name == "temporal_graph":
        from agents.temporal_graph_agent import TemporalGraphAgent
        AGENT_REGISTRY["temporal_graph"] = TemporalGraphAgent
        return TemporalGraphAgent
    elif name == "topic_modeling":
        from agents.topic_modeling_agent import TopicModelingAgent
        AGENT_REGISTRY["topic_modeling"] = TopicModelingAgent
        return TopicModelingAgent
    elif name == "relationship_extractor":
        from agents.relationship_extractor_agent import RelationshipExtractorAgent
        AGENT_REGISTRY["relationship_extractor"] = RelationshipExtractorAgent
        return RelationshipExtractorAgent
    elif name == "trend_detector":
        from agents.trend_detector_agent import TrendDetectorAgent
        AGENT_REGISTRY["trend_detector"] = TrendDetectorAgent
        return TrendDetectorAgent
    elif name == "intent_classifier":
        from agents.intent_classifier_agent import IntentClassifierAgent
        AGENT_REGISTRY["intent_classifier"] = IntentClassifierAgent
        return IntentClassifierAgent
    elif name == "sector_rotation":
        from agents.sector_rotation_agent import SectorRotationAgent
        AGENT_REGISTRY["sector_rotation"] = SectorRotationAgent
        return SectorRotationAgent
    elif name == "cohort_analysis":
        from agents.cohort_analysis_agent import CohortAnalysisAgent
        AGENT_REGISTRY["cohort_analysis"] = CohortAnalysisAgent
        return CohortAnalysisAgent
    elif name == "slack_integration":
        from agents.slack_integration_agent import SlackIntegrationAgent
        AGENT_REGISTRY["slack_integration"] = SlackIntegrationAgent
        return SlackIntegrationAgent
    elif name == "email_digest":
        from agents.email_digest_agent import EmailDigestAgent
        AGENT_REGISTRY["email_digest"] = EmailDigestAgent
        return EmailDigestAgent
    elif name == "export":
        from agents.export_agent import ExportAgent
        AGENT_REGISTRY["export"] = ExportAgent
        return ExportAgent
    elif name == "feed_generator":
        from agents.feed_generator_agent import FeedGeneratorAgent
        AGENT_REGISTRY["feed_generator"] = FeedGeneratorAgent
        return FeedGeneratorAgent
    elif name == "data_quality":
        from agents.data_quality_agent import DataQualityAgent
        AGENT_REGISTRY["data_quality"] = DataQualityAgent
        return DataQualityAgent
    elif name == "pipeline_health":
        from agents.pipeline_health_agent import PipelineHealthAgent
        AGENT_REGISTRY["pipeline_health"] = PipelineHealthAgent
        return PipelineHealthAgent
    elif name == "cost_tracking":
        from agents.cost_tracking_agent import CostTrackingAgent
        AGENT_REGISTRY["cost_tracking"] = CostTrackingAgent
        return CostTrackingAgent

    # ── AI Product Development Team (7 agents) ──
    elif name == "product_manager":
        from agents.product_manager_agent import ProductManagerAgent
        AGENT_REGISTRY["product_manager"] = ProductManagerAgent
        return ProductManagerAgent
    elif name == "business_analyst":
        from agents.business_analyst_agent import BusinessAnalystAgent
        AGENT_REGISTRY["business_analyst"] = BusinessAnalystAgent
        return BusinessAnalystAgent
    elif name == "solution_architect":
        from agents.solution_architect_agent import SolutionArchitectAgent
        AGENT_REGISTRY["solution_architect"] = SolutionArchitectAgent
        return SolutionArchitectAgent
    elif name == "ux_designer":
        from agents.ux_designer_agent import UXDesignerAgent
        AGENT_REGISTRY["ux_designer"] = UXDesignerAgent
        return UXDesignerAgent
    elif name == "software_engineer":
        from agents.software_engineer_agent import SoftwareEngineerAgent
        AGENT_REGISTRY["software_engineer"] = SoftwareEngineerAgent
        return SoftwareEngineerAgent
    elif name == "qa_engineer":
        from agents.qa_engineer_agent import QAEngineerAgent
        AGENT_REGISTRY["qa_engineer"] = QAEngineerAgent
        return QAEngineerAgent
    elif name == "devops_engineer":
        from agents.devops_engineer_agent import DevOpsEngineerAgent
        AGENT_REGISTRY["devops_engineer"] = DevOpsEngineerAgent
        return DevOpsEngineerAgent
    elif name == "feedback_analyzer":
        from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent
        AGENT_REGISTRY["feedback_analyzer"] = FeedbackAnalyzerAgent
        return FeedbackAnalyzerAgent

    raise ValueError(f"Unknown agent: {name}")


class OrchestratorAgent(BaseAgent):
    """Agent that coordinates the full research pipeline.

    Reads the pipeline definition from config and runs agents sequentially,
    passing upstream_results between stages.

    Config options:
        continue_on_failure: bool — continue pipeline if an agent fails
        pipelines: dict mapping pipeline names to lists of agent names
    """

    @property
    def name(self) -> str:
        return "orchestrator"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        pipeline_name = self.config.get("_pipeline_name", "daily")
        continue_on_failure = self.config.get("continue_on_failure", True)
        pipelines = self.config.get("pipelines", {
            "daily": ["collection", "report"],
            "weekly": ["collection", "report"],
            "dev-team": ["product_manager", "business_analyst", "solution_architect",
                         "ux_designer", "software_engineer", "qa_engineer",
                         "devops_engineer"],
        })

        agent_names = pipelines.get(pipeline_name, pipelines.get("daily", ["collection", "report"]))

        _logger.info("Orchestrator: Starting pipeline '%s' with %d stages",
                     pipeline_name, len(agent_names))
        _logger.info("Orchestrator: Stages: %s", " → ".join(agent_names))

        # Check feedback analyzer output for priority adjustments
        feedback_priority = self._check_feedback_priorities()
        if feedback_priority:
            _logger.info("Orchestrator: Feedback priorities detected: %s", feedback_priority)

        all_results = []
        overall_status = "success"
        start_time = datetime.now(timezone.utc)

        for agent_name in agent_names:
            try:
                agent_class = _get_agent_class(agent_name)
            except ValueError as e:
                _logger.error("Orchestrator: %s — skipping", e)
                all_results.append(AgentResult(
                    agent_name=agent_name, status="failed", errors=[str(e)]
                ))
                overall_status = "partial"
                continue

            # Build agent config by merging orchestrator settings with agent-specific config
            agent_config = self.config.get(agent_name, {})
            agent_config["_pipeline_name"] = pipeline_name
            agent_config["_scheduled"] = self.config.get("_scheduled", False)

            # Pass daily_mode to collection agent for daily pipelines
            if agent_name == "collection" and pipeline_name == "daily":
                agent_config["daily_mode"] = True

            agent = agent_class(config=agent_config, dry_run=self.dry_run)
            result = agent.run(upstream_results=all_results)
            all_results.append(result)

            if result.status == "failed":
                if continue_on_failure:
                    _logger.warning("Orchestrator: '%s' failed — continuing (continue_on_failure=True)",
                                    agent_name)
                    overall_status = "partial"
                else:
                    _logger.error("Orchestrator: '%s' failed — halting pipeline", agent_name)
                    overall_status = "failed"
                    break

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

        _logger.info("=" * 60)
        _logger.info("ORCHESTRATOR SUMMARY — pipeline '%s' (%.1fs)", pipeline_name, elapsed)
        _logger.info("=" * 60)
        for r in all_results:
            _logger.info("  %-25s status=%-8s errors=%d",
                         r.agent_name, r.status, len(r.errors))
        _logger.info("Overall: %s", overall_status)

        return AgentResult(
            agent_name=self.name,
            status=overall_status,
            data={
                "pipeline_name": pipeline_name,
                "elapsed_seconds": elapsed,
                "agents_run": len(all_results),
                "records_affected": sum(
                    r.data.get("records_affected", 0) for r in all_results if r.data
                ),
                "agent_results": [
                    {"name": r.agent_name, "status": r.status, "data": r.data}
                    for r in all_results
                ],
            },
            errors=[e for r in all_results for e in r.errors],
        )

    def _check_feedback_priorities(self) -> dict:
        """Check feedback_analysis for priority signals (best-effort)."""
        try:
            from db.connection import get_connection
            import json as _json

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT trending_queries, top_feature_requests "
                "FROM feedback_analysis ORDER BY analyzed_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return {}
            priorities = {}
            queries = _json.loads(row.get("trending_queries", "[]") or "[]")
            if queries:
                themes = set()
                for q in queries[:5]:
                    words = q.get("query", "").lower().split()
                    themes.update(w for w in words if len(w) > 4)
                priorities["trending_themes"] = list(themes)[:10]
            features = _json.loads(row.get("top_feature_requests", "[]") or "[]")
            if features:
                priorities["requested_features"] = [
                    f.get("feature", "") for f in features[:3]
                ]
            return priorities
        except Exception:
            return {}
