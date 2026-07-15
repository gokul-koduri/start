#!/usr/bin/env python3
"""CLI entry point for pre-generating LLM-powered report insights.

Usage:
    # Generate all insights (run before report generation)
    python scripts/generate_report_insights.py

    # Generate specific insight type
    python scripts/generate_report_insights.py --section executive_summary

    # Force regeneration (ignore cache)
    python scripts/generate_report_insights.py --force

    # Generate to specific report section
    python scripts/generate_report_insights.py --section failure_patterns --force

    # List available insight types
    python scripts/generate_report_insights.py --list
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import setup_logging, load_config
from db.connection import get_connection
from db import schema
from report.llm_insights_agent import (
    run_insights_analysis,
    clear_insights_cache,
    DEFAULT_MODEL,
)

_logger = logging.getLogger("generate_report_insights")

AVAILABLE_INSIGHTS = {
    "executive_summary": "AI-generated executive summary of the full report",
    "failure_patterns": "AI analysis of failure patterns by sector",
    "revival_opportunities": "AI evaluation of manufacturing revival opportunities",
    "cross_references": "AI identification of failure-to-opportunity connections",
    "opportunity_rankings": "AI-ranked actionable opportunities",
    "news_intelligence": "AI synthesis of recent news articles",
}


def main():
    parser = argparse.ArgumentParser(
        description="Pre-generate LLM-powered insights for the report. "
        "Run this before generating the report with --include-llm-insights.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_report_insights.py
  python scripts/generate_report_insights.py --section failure_patterns
  python scripts/generate_report_insights.py --force
  python scripts/generate_report_insights.py --list
        """,
    )
    parser.add_argument(
        "--section",
        "-s",
        type=str,
        default=None,
        choices=list(AVAILABLE_INSIGHTS.keys()),
        help="Generate only a specific insight type",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force regeneration (ignore cache)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the insight cache before generating",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available insight types",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    setup_logging()

    # List mode
    if args.list:
        print("Available insight types:")
        print()
        for key, desc in AVAILABLE_INSIGHTS.items():
            print(f"  {key:25s} - {desc}")
        print()
        return

    # Open DB
    _logger.info("Connecting to database...")
    conn = get_connection()
    schema.init_schema(conn)
    _logger.info("Database connected")

    try:
        # Clear cache if requested
        if args.clear_cache:
            _logger.info("Clearing insights cache...")
            clear_insights_cache()
            _logger.info("Cache cleared")

        # Override model from config
        config = load_config()
        config["ollama"] = config.get("ollama", {})
        config["ollama"]["model"] = args.model

        # Run insights
        section = args.section
        _logger.info(
            "Running LLM insights analysis%s...",
            f" for '{section}'" if section else " (all insights)",
        )

        results = run_insights_analysis(
            conn,
            config,
            section=section,
            force_refresh=args.force,
        )

        # Report results
        print()
        print("=" * 60)
        print("LLM Insights Generation Results")
        print("=" * 60)

        success_count = sum(1 for v in results.values() if v is not None)
        total_count = len(results)

        for insight_type, content in results.items():
            status_icon = "OK" if content else "SKIP"
            print(f"  [{status_icon}] {insight_type}")

        print()
        print(f"Summary: {success_count}/{total_count} insights generated successfully")

        if args.force:
            print("(Cache was ignored due to --force flag)")

        if success_count < total_count:
            print()
            print("Some insights were not generated. This may be because:")
            print("  - Ollama is not running (start with: ollama serve)")
            print("  - No relevant data in the database for that section")
            print("  - LLM returned an empty response")
            _logger.warning(
                "%d/%d insights failed to generate", total_count - success_count, total_count
            )

    finally:
        conn.close()
        _logger.info("Database connection closed")


if __name__ == "__main__":
    main()