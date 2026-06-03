#!/usr/bin/env python3
"""Entry point to run the automated agent pipeline.

Usage:
    python run_agent.py --pipeline daily          # Daily: fast collectors + report + publish
    python run_agent.py --pipeline weekly         # Weekly: all collectors + research + publish
    python run_agent.py --pipeline analysis       # Run all analysis agents
    python run_agent.py --pipeline full           # Collection + analysis + dashboard + publish
    python run_agent.py --pipeline collect-only   # Only run data collection
    python run_agent.py --pipeline report-only    # Only generate report
    python run_agent.py --pipeline publish-only   # Only publish (dashboard + git)
    python run_agent.py --chat "query"           # Ask a natural language question (AI Analyst)
    python run_agent.py --pipeline daily --dry-run
"""

import argparse
import fcntl
import logging
import os
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
        logging.error("Could not acquire lock — another pipeline run may be in progress: %s", e)
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
        choices=["daily", "weekly", "analysis", "full", "collect-only", "report-only", "publish-only"],
        default="daily",
        help="Which pipeline to run (default: daily)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Log actions without making changes")
    parser.add_argument("--force", action="store_true", help="Force run even if no new data")
    parser.add_argument(
        "--chat",
        type=str,
        default=None,
        help="Ask a natural language question about the data (AI Analyst mode)",
    )

    args = parser.parse_args()

    setup_logging()
    _logger = logging.getLogger("run_agent")
    config = load_config()

    # AI Analyst mode: direct query, bypass pipeline
    if args.chat:
        _logger.info("AI Analyst mode — query: %s", args.chat[:80])
        agents_config = config.get("agents", {})
        analyst_config = agents_config.get("ai_analyst", {})
        analyst_config["_pipeline_name"] = "chat"
        analyst_config["_scheduled"] = False

        from agents.ai_analyst_agent import AIAnalystAgent
        analyst = AIAnalystAgent(config=analyst_config, dry_run=args.dry_run, query=args.chat)
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
        for key in ["collection", "report", "dashboard", "git_publisher", "internet_research",
                     "failure_pattern", "survival_analysis", "revival_opportunity",
                     "geographic_strategy", "news_intelligence", "opportunity_pipeline",
                     "whale_investor", "correlation", "global_market_viability",
                     "llm_pricing", "llm_benchmark", "llm_portfolio", "llm_cost_optimizer",
                     "license_manager", "knowledge_graph", "ai_analyst",
                     "alert_dispatcher", "report_generator", "stripe_payments", "span_monitor"]:
            if key in agents_config:
                orchestrator_config[key] = agents_config[key]

        if args.force and "report" in orchestrator_config:
            orchestrator_config["report"]["only_on_new_data"] = False

        orchestrator = OrchestratorAgent(config=orchestrator_config, dry_run=args.dry_run)
        result = orchestrator.run()

        # Exit with error code if pipeline failed
        sys.exit(1 if result.status == "failed" else 0)

    finally:
        release_lock()


if __name__ == "__main__":
    main()
