#!/usr/bin/env python3
"""Entry point to run data collectors.

Usage:
    python run_collectors.py --all                      # Run all collectors
    python run_collectors.py --collector bls_survival_rates  # Run one collector
    python run_collectors.py --all --dry-run             # Log what would happen
    python run_collectors.py --all --force               # Ignore incremental state
"""

import argparse
import fcntl
import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_project_root, setup_logging, load_config
from db import schema
from db.connection import get_connection
from collectors.bls_survival_rates import BLSSurvivalRateCollector
from collectors.google_news_rss import GoogleNewsRSSCollector
from collectors.techcrunch_rss import TechCrunchRSSCollector
from collectors.failory_scraper import FailoryScraper
from collectors.reshoring_pdf import ReshoringPDFCollector

ALL_COLLECTORS = {
    "bls_survival_rates": BLSSurvivalRateCollector,
    "google_news_rss": GoogleNewsRSSCollector,
    "techcrunch_rss": TechCrunchRSSCollector,
    "failory_scraper": FailoryScraper,
    "reshoring_pdf": ReshoringPDFCollector,
}

LOCK_FILE = None


def acquire_lock():
    """Acquire an exclusive file lock to prevent concurrent runs."""
    global LOCK_FILE
    lock_path = get_project_root() / "data" / "collectors.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        LOCK_FILE = open(lock_path, "w")
        fcntl.flock(LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError, OSError) as e:
        logging.error(
            "Could not acquire lock — another collection run may be in progress: %s", e
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
    parser = argparse.ArgumentParser(description="Run startup research data collectors")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Run all enabled collectors")
    group.add_argument("--collector", type=str, help="Run a specific collector by name")
    parser.add_argument(
        "--dry-run", action="store_true", help="Log actions without writing to DB"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore incremental state, collect everything",
    )

    args = parser.parse_args()

    # Setup
    setup_logging()
    _logger = logging.getLogger("run_collectors")
    config = load_config()

    _logger.info("Startup Research Data Collector")
    _logger.info("Project root: %s", get_project_root())

    # Acquire lock
    if not acquire_lock():
        sys.exit(1)

    try:
        # Ensure DB exists and schema is current
        conn = get_connection()
        schema.init_schema(conn)
        conn.close()

        # Determine which collectors to run
        if args.all:
            collector_names = list(ALL_COLLECTORS.keys())
        else:
            collector_names = [args.collector]

        # Run each collector
        results = []
        for name in collector_names:
            if name not in ALL_COLLECTORS:
                _logger.error("Unknown collector: %s", name)
                results.append((name, "unknown", 0, 0, 0, ["Unknown collector"]))
                continue

            collector_class = ALL_COLLECTORS[name]
            collector = collector_class(config=config, dry_run=args.dry_run)
            result = collector.run()
            results.append(
                (
                    name,
                    result.status,
                    result.records_collected,
                    result.records_inserted,
                    result.records_skipped,
                    result.errors,
                )
            )

        # Print summary
        _logger.info("=" * 60)
        _logger.info("COLLECTION SUMMARY")
        _logger.info("=" * 60)
        for name, status, collected, inserted, skipped, errors in results:
            _logger.info(
                "  %-25s status=%-8s collected=%-4d inserted=%-4d skipped=%-4d errors=%d",
                name,
                status,
                collected,
                inserted,
                skipped,
                len(errors),
            )

        # Exit code
        has_failure = any(s == "failed" for _, s, *_ in results)
        sys.exit(1 if has_failure else 0)

    finally:
        release_lock()


if __name__ == "__main__":
    main()
