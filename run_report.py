#!/usr/bin/env python3
"""Entry point to generate the markdown report from the MySQL database.

Usage:
    python run_report.py                                 # Generate full report
    python run_report.py --output path/to/report.md      # Custom output path
    python run_report.py --section part1                 # Generate only Part 1
    python run_report.py --include-llm-insights          # Include LLM-generated insights
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_project_root, setup_logging, load_config
from db.connection import get_connection
from db import schema
from report.generator import generate_report

_logger = logging.getLogger("run_report")


def main():
    parser = argparse.ArgumentParser(description="Generate startup research report")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: from config)",
    )
    parser.add_argument(
        "--section",
        type=str,
        default=None,
        help="Generate only a specific section (e.g., part1, part2)",
    )
    parser.add_argument(
        "--include-llm-insights",
        action="store_true",
        help="Include LLM-generated insights (requires pre-generated insights via "
        "scripts/generate_report_insights.py, or Ollama running for on-demand generation)",
    )

    args = parser.parse_args()

    # Setup
    setup_logging()
    config = load_config()

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = get_project_root() / config.get("report", {}).get(
            "output_path", "Failed_Startups_Manufacturing_Revival_Report.md"
        )

    _logger.info("Generating report: %s", output_path)

    # Open DB
    conn = get_connection()
    schema.init_schema(conn)

    try:
        result_path = generate_report(
            conn, config, str(output_path), section=args.section,
            include_llm_insights=args.include_llm_insights,
        )
        _logger.info("Report written to: %s", result_path)
    finally:
        conn.close()


if __name__ == "__main__":
    main()