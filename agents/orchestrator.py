"""Orchestrator agent — composes and runs the full agent pipeline."""

import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from agents.collection import CollectionAgent
from agents.report import ReportAgent

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
        from agents.dashboard import DashboardAgent
        AGENT_REGISTRY["dashboard"] = DashboardAgent
        return DashboardAgent
    elif name == "git_publisher":
        from agents.git_publisher import GitPublisherAgent
        AGENT_REGISTRY["git_publisher"] = GitPublisherAgent
        return GitPublisherAgent
    elif name == "internet_research":
        from agents.internet_research import InternetResearchAgent
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
        })

        agent_names = pipelines.get(pipeline_name, pipelines.get("daily", ["collection", "report"]))

        _logger.info("Orchestrator: Starting pipeline '%s' with %d stages",
                     pipeline_name, len(agent_names))
        _logger.info("Orchestrator: Stages: %s", " → ".join(agent_names))

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
