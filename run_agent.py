#!/usr/bin/env python3
"""Entry point to run the automated agent pipeline.

Usage:
    # Traditional pipelines
    python run_agent.py --pipeline daily          # Daily: fast collectors + report + publish
    python run_agent.py --pipeline weekly         # Weekly: all collectors + research + publish
    python run_agent.py --pipeline analysis       # Run all analysis agents
    python run_agent.py --pipeline full           # Collection + analysis + dashboard + publish

    # Unified Span Agent (Tasks 2, 3, 4)
    python run_agent.py --span run --pipeline daily    # Task 2: Run pipeline
    python run_agent.py --span status                  # Task 2: Get pipeline status
    python run_agent.py --span ask "query"             # Task 4: Research query
    python run_agent.py --span report --type opportunity --topic "Ohio EV Battery"  # Task 3: Generate report
    python run_agent.py --span report --list-templates # List available report templates
    python run_agent.py --span opportunities --min-score 70  # Task 4: Find opportunities

    # Direct chat
    python run_agent.py --chat "query"           # Ask a natural language question (AI Analyst)
    python run_agent.py --pipeline daily --dry-run
"""

import argparse
import fcntl
import json
import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_project_root, setup_logging, load_config
from agents.orchestrator import OrchestratorAgent

LOCK_FILE = None


def acquire_lock():
    """Acquire an exclusive file lock to prevent concurrent pipeline runs."""
    global LOCK_FILE
    lock_path = get_project_root() / "data" / "agents.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        LOCK_FILE = open(lock_path, "w")
        fcntl.flock(LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError, OSError) as e:
        logging.error(
            "Could not acquire lock — another pipeline run may be in progress: %s", e
        )
        return False


def release_lock():
    """Release the file lock."""
    global LOCK_FILE
    if LOCK_FILE:
        try:
            fcntl.flock(LOCK_FILE, fcntl.LOCK_UN)
            LOCK_FILE.close()
        except Exception:
            pass
        LOCK_FILE = None


def main():
    parser = argparse.ArgumentParser(description="Run startup research agent pipeline")
    parser.add_argument(
        "--pipeline",
        choices=[
            "daily",
            "weekly",
            "analysis",
            "full",
            "collect-only",
            "report-only",
            "publish-only",
            "dev-team",
            "sprint-cycle",
            "sprint-execution",
            # Span mode pipelines
            "span-only",
            "span-report",
            "span-research",
        ],
        default="daily",
        help="Which pipeline to run (default: daily)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log actions without making changes"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force run even if no new data"
    )
    parser.add_argument(
        "--chat",
        type=str,
        default=None,
        help="Ask a natural language question about the data (AI Analyst mode)",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Run a single agent by name (e.g. product_manager, qa_engineer)",
    )
    # Unified Span Agent CLI (Tasks 2, 3, 4)
    parser.add_argument(
        "--span",
        type=str,
        default=None,
        choices=["run", "status", "ask", "report", "compare", "opportunities"],
        help="Unified Span Agent operations: run pipeline, get status, ask queries, generate reports",
    )
    parser.add_argument(
        "--pipeline-arg",
        type=str,
        default=None,
        dest="pipeline_arg",
        help="Pipeline name for --span run (default: daily)",
    )
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        dest="report_type",
        help="Report template type for --span report (opportunity_report, market_viability_report, startup_success_report)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Topic for --span report",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Query for --span ask or --span opportunities",
    )
    parser.add_argument(
        "--sectors",
        type=str,
        nargs="+",
        default=None,
        help="Sectors for --span compare",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=None,
        dest="min_score",
        help="Minimum opportunity score for --span opportunities",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        default=False,
        dest="list_templates",
        help="List available report templates",
    )

    args = parser.parse_args()

    setup_logging()
    _logger = logging.getLogger("run_agent")
    config = load_config()

    # Single agent mode: run one agent directly
    if args.agent:
        # Redirect ALL logging to stderr so JSON output on stdout is clean
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)
            if hasattr(handler, "stream") and handler.stream == sys.stdout:
                handler.stream = sys.stderr
                logging.getLogger().addHandler(handler)
            else:
                logging.getLogger().addHandler(handler)
        for name in logging.root.manager.loggerDict:
            lg = logging.getLogger(name)
            for h in lg.handlers[:]:
                if hasattr(h, "stream") and h.stream == sys.stdout:
                    lg.removeHandler(h)
                    h.stream = sys.stderr
                    lg.addHandler(h)

        _logger.info("Single agent mode — agent: %s", args.agent)
        from agents.orchestrator import _get_agent_class

        try:
            agent_class = _get_agent_class(args.agent)
        except ValueError:
            _logger.error("Unknown agent: %s", args.agent)
            sys.exit(1)

        agent = agent_class(config={}, dry_run=args.dry_run)
        result = agent.run()

        # Print summary to stderr (logging)
        _logger.info("Agent '%s' finished: status=%s", result.agent_name, result.status)
        if result.errors:
            for err in result.errors:
                _logger.error("  Error: %s", err)

        # Print JSON to stdout only
        import json as _json

        output = {"status": result.status, "agent_name": result.agent_name}
        if result.errors:
            output["errors"] = result.errors
        if result.data:
            output["data"] = result.data
        print(_json.dumps(output, indent=2, default=str))

        sys.exit(1 if result.status == "failed" else 0)

    # ── Unified Span Agent Mode (Tasks 2, 3, 4) ──────────────────────────────
    # Note: --list-templates is also handled here (requires --span report)
    if args.span or args.list_templates:
        from agents.span_agent import SpanAgent

        # Always show templates if requested
        if args.list_templates:
            templates = [
                {"name": "opportunity_report", "description": "Manufacturing revival opportunities"},
                {"name": "market_viability_report", "description": "Global market analysis"},
                {"name": "startup_success_report", "description": "Success pattern analysis"},
            ]
            print(json.dumps(templates, indent=2))
            sys.exit(0)

        _logger.info("Span Agent mode — action: %s", args.span)

        span_config = config.get("agents", {}).get("span", {})
        span_config["_pipeline_name"] = f"span-{args.span}"
        span_config["_scheduled"] = False

        span_agent = SpanAgent(config=span_config, dry_run=args.dry_run)

        # Route to appropriate span method
        if args.span == "status":
            result = span_agent.run_unified("status")
        elif args.span == "ask":
            if not args.query:
                _logger.error("--span ask requires --query")
                sys.exit(1)
            result = span_agent.run_unified("ask", query=args.query)
        elif args.span == "report":
            result = span_agent.run_unified(
                "report",
                type=args.report_type or "opportunity_report",
                topic=args.topic or "",
            )
        elif args.span == "compare":
            if not args.sectors:
                _logger.error("--span compare requires --sectors")
                sys.exit(1)
            result = span_agent.run_unified("compare", sectors=args.sectors)
        elif args.span == "opportunities":
            criteria = {}
            if args.min_score:
                criteria["min_opportunity_score"] = args.min_score
            result = span_agent.run_unified("opportunities", criteria=criteria)
        else:
            # args.span == "run"
            pipeline_name = args.pipeline_arg or args.pipeline or "daily"
            result = span_agent.run_unified("run", pipeline=pipeline_name)

        sys.exit(1 if result.status == "failed" else 0)

    # AI Analyst mode: direct query, bypass pipeline
    if args.chat:
        _logger.info("AI Analyst mode — query: %s", args.chat[:80])
        agents_config = config.get("agents", {})
        analyst_config = agents_config.get("ai_analyst", {})
        analyst_config["_pipeline_name"] = "chat"
        analyst_config["_scheduled"] = False

        from agents.ai_analyst_agent import AIAnalystAgent

        analyst = AIAnalystAgent(
            config=analyst_config, dry_run=args.dry_run, query=args.chat
        )
        result = analyst.run()
        sys.exit(1 if result.status == "failed" else 0)

    _logger.info("Startup Research Agent Pipeline")
    _logger.info("Project root: %s", get_project_root())
    _logger.info("Pipeline: %s", args.pipeline)

    # Acquire lock
    if not acquire_lock():
        sys.exit(1)

    try:
        agents_config = config.get("agents", {})
        orchestrator_config = agents_config.get("orchestrator", {})
        orchestrator_config["_pipeline_name"] = args.pipeline
        orchestrator_config["_scheduled"] = False
        orchestrator_config["dry_run"] = args.dry_run

        # Merge in agent-specific configs
        for key in [
            "collection",
            "report",
            "dashboard",
            "git_publisher",
            "internet_research",
            "failure_pattern",
            "survival_analysis",
            "revival_opportunity",
            "geographic_strategy",
            "news_intelligence",
            "opportunity_pipeline",
            "whale_investor",
            "correlation",
            "global_market_viability",
            "llm_pricing",
            "llm_benchmark",
            "llm_portfolio",
            "llm_cost_optimizer",
            "license_manager",
            "knowledge_graph",
            "ai_analyst",
            "alert_dispatcher",
            "sprint_cycle",
            "sprint_execution",
            "sprint_execution_agent",
            "report_generator",
            "stripe_payments",
            "span_monitor",
            "opportunity_scorer",
            "entity_resolver",
            "nlp_enrichment",
            "semantic_search",
            # AI Product Development Team
            "product_manager",
            "business_analyst",
            "solution_architect",
            "ux_designer",
            "software_engineer",
            "qa_engineer",
            "devops_engineer",
        ]:
            if key in agents_config:
                orchestrator_config[key] = agents_config[key]

        if args.force and "report" in orchestrator_config:
            orchestrator_config["report"]["only_on_new_data"] = False

        # Sprint Cycle pipelines (continuous execution)
        if args.pipeline == "sprint-cycle":
            _logger.info("Starting Sprint Cycle Agent (continuous)")
            from agents.cycle_agent import CycleAgent
            sprint_config = config.get("sprint_cycle", {})
            agent = CycleAgent(config=sprint_config, dry_run=args.dry_run)
            agent.run_continuous()
            sys.exit(0)

        if args.pipeline == "sprint-execution":
            _logger.info("Starting Sprint Execution Agent")
            from agents.sprint_execution_agent import SprintExecutionAgent
            agent = SprintExecutionAgent(config={}, dry_run=args.dry_run)
            result = agent.run()
            sys.exit(1 if result.status == "failed" else 0)

        orchestrator = OrchestratorAgent(
            config=orchestrator_config, dry_run=args.dry_run
        )
        result = orchestrator.run()

        # Exit with error code if pipeline failed
        sys.exit(1 if result.status == "failed" else 0)

    finally:
        release_lock()


if __name__ == "__main__":
    main()
