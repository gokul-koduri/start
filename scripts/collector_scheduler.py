#!/usr/bin/env python3
"""Collector scheduler — runs collectors on configurable intervals 24/7.

Usage:
    python scripts/collector_scheduler.py                   # Run with config
    python scripts/collector_scheduler.py --once             # Run all once and exit
    python scripts/collector_scheduler.py --group fast       # Run only fast group
    python scripts/collector_scheduler.py --collector hn_live  # Run one collector

Docker:
    Added as `scheduler` service in docker-compose.yml.
    Depends on MySQL health check. Restart policy: unless-stopped.
"""

import argparse
import json
import logging
import signal
import sys
import time
import threading
import fcntl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_project_root, setup_logging, load_config

_logger = logging.getLogger("collector_scheduler")

# Global shutdown flag
_shutdown = threading.Event()
LOCK_FILE = None

# ── Collector Registry ────────────────────────────────────
# Reuse the same registry as agents/collection_agent.py
# Lazy imports to avoid loading all collectors at startup

COLLECTOR_CLASSES = {
    "bls_survival_rates": "collectors.bls_survival_rates.BLSSurvivalRateCollector",
    "google_news_rss": "collectors.google_news_rss.GoogleNewsRSSCollector",
    "techcrunch_rss": "collectors.techcrunch_rss.TechCrunchRSSCollector",
    "failory_scraper": "collectors.failory_scraper.FailoryScraper",
    "reshoring_pdf": "collectors.reshoring_pdf.ReshoringPDFCollector",
    "github_deep": "collectors.github_deep_collector.GithubDeepCollector",
    "reddit_stream": "collectors.reddit_stream_collector.RedditStreamCollector",
    "hn_live": "collectors.hn_live_collector.HNLiveCollector",
    "opencorporates": "collectors.opencorporates_collector.OpenCorporatesCollector",
    "arxiv": "collectors.arxiv_collector.ArxivCollector",
    "producthunt": "collectors.producthunt_collector.ProductHuntCollector",
    "website_monitor": "collectors.website_monitor_collector.WebsiteMonitorCollector",
    "twitter": "collectors.twitter_collector.TwitterCollector",
    "stackoverflow": "collectors.stackoverflow_collector.StackOverflowCollector",
    "npm_pypi": "collectors.npm_pypi_collector.NPMPyPICollector",
    "regulatory": "collectors.regulatory_collector.RegulatoryCollector",
    "newsletter": "collectors.newsletter_collector.NewsletterCollector",
    "sec_edgar": "collectors.sec_edgar_collector.SECEdgarCollector",
    "patents": "collectors.patent_collector.PatentCollector",
    "social_media": "collectors.social_media_collector.SocialMediaCollector",
    "funding_events": "collectors.funding_events_collector.FundingEventsCollector",
    "github_trends": "collectors.github_trends_collector.GithubTrendsCollector",
    "crunchbase": "collectors.crunchbase.CrunchBaseCollector",
    "job_postings": "collectors.job_postings_collector.JobPostingsCollector",
}


def _get_collector_class(name: str):
    """Import and return a collector class by name."""
    if name not in COLLECTOR_CLASSES:
        raise ValueError(f"Unknown collector: {name}")
    module_path, class_name = COLLECTOR_CLASSES[name].rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


# ── Retry Logic ───────────────────────────────────────────

def _is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    msg = str(error).lower()
    permanent_indicators = [
        "401", "403", "unauthorized", "forbidden", "invalid api key",
        "not found", "404", "config", "no .* configured",
    ]
    import re
    for pattern in permanent_indicators:
        if re.search(pattern, msg):
            return False
    return True


def run_with_retry(collector_name: str, config: dict, max_retries: int = 3,
                   backoff_seconds: list | None = None) -> dict:
    """Run a collector with retry logic and exponential backoff.

    Returns a result dict: {name, status, records_collected, attempts, errors}
    """
    if backoff_seconds is None:
        backoff_seconds = [30, 60, 120]

    collector_class = _get_collector_class(collector_name)
    attempts = 0
    last_error = None

    for attempt in range(max_retries):
        if _shutdown.is_set():
            return {"name": collector_name, "status": "skipped", "attempts": attempts, "errors": ["shutdown"]}

        attempts += 1
        try:
            collector = collector_class(config=config)
            result = collector.run()

            if result.status in ("success", "partial"):
                return {
                    "name": collector_name,
                    "status": result.status,
                    "records_collected": result.records_collected,
                    "records_inserted": result.records_inserted,
                    "attempts": attempts,
                    "errors": result.errors,
                }

            # Failed — decide if retryable
            last_error = "; ".join(result.errors[:3]) if result.errors else "unknown error"
            if not _is_transient_error(Exception(last_error)):
                _logger.warning("%s: permanent error (not retrying): %s", collector_name, last_error)
                break

            if attempt < max_retries - 1:
                wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                _logger.warning(
                    "%s: attempt %d/%d failed (%s) — retrying in %ds",
                    collector_name, attempts, max_retries, last_error, wait,
                )
                _shutdown.wait(wait)  # Uses Event.wait so shutdown interrupts sleep

        except Exception as e:
            last_error = str(e)
            _logger.error("%s: attempt %d/%d exception: %s", collector_name, attempts, max_retries, e)
            if not _is_transient_error(e):
                break
            if attempt < max_retries - 1:
                wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                _shutdown.wait(wait)

    return {
        "name": collector_name,
        "status": "failed",
        "records_collected": 0,
        "attempts": attempts,
        "errors": [last_error or "all retries exhausted"],
    }


# ── Scheduler Core ────────────────────────────────────────

def run_group(collector_names: list[str], config: dict, scheduler_config: dict) -> list[dict]:
    """Run a group of collectors with concurrency limit."""
    max_concurrent = scheduler_config.get("max_concurrent", 3)
    retry_config = scheduler_config.get("retry", {})
    max_retries = retry_config.get("max_attempts", 3)
    backoff = retry_config.get("backoff_seconds", [30, 60, 120])
    timeout = scheduler_config.get("collector_timeout", 300)

    results = []
    _logger.info("Running %d collectors (max %d concurrent)", len(collector_names), max_concurrent)

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {}
        for name in collector_names:
            if _shutdown.is_set():
                break
            future = executor.submit(run_with_retry, name, config, max_retries, backoff)
            futures[future] = name

        for future in as_completed(futures, timeout=timeout * len(collector_names)):
            if _shutdown.is_set():
                break
            try:
                result = future.result(timeout=timeout)
                results.append(result)
            except Exception as e:
                name = futures[future]
                results.append({"name": name, "status": "failed", "attempts": 0, "errors": [str(e)]})

    return results


def run_all_groups(config: dict) -> list[dict]:
    """Run all collector groups defined in scheduler config."""
    scheduler_config = config.get("scheduler", {})
    groups = scheduler_config.get("groups", {})
    all_results = []

    for group_name, group_def in groups.items():
        if _shutdown.is_set():
            break
        collectors = group_def.get("collectors", [])
        _logger.info("── Group '%s': %d collectors ──", group_name, len(collectors))
        group_results = run_group(collectors, config, scheduler_config)
        all_results.extend(group_results)

        success = sum(1 for r in group_results if r["status"] in ("success", "partial"))
        _logger.info("── Group '%s' done: %d/%d succeeded ──", group_name, success, len(group_results))

    return all_results


def print_summary(results: list[dict]):
    """Print a human-readable summary of collection results."""
    _logger.info("=" * 60)
    _logger.info("COLLECTION SCHEDULE SUMMARY")
    _logger.info("=" * 60)
    total = len(results)
    success = sum(1 for r in results if r["status"] in ("success", "partial"))
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    total_records = sum(r.get("records_collected", 0) for r in results)

    for r in sorted(results, key=lambda x: x["status"]):
        icon = {"success": "+", "partial": "~", "failed": "X", "skipped": "-"}
        _logger.info(
            "  [%s] %-25s status=%-8s collected=%-4d attempts=%d",
            icon.get(r["status"], "?"), r["name"], r["status"],
            r.get("records_collected", 0), r.get("attempts", 1),
        )
        if r.get("errors"):
            for err in r["errors"][:2]:
                _logger.info("       → %s", err[:100])

    _logger.info("-" * 60)
    _logger.info("Total: %d collectors, %d succeeded, %d failed, %d skipped, %d records",
                 total, success, failed, skipped, total_records)
    _logger.info("=" * 60)


# ── Daemon Loop ───────────────────────────────────────────

def acquire_lock():
    """Acquire exclusive file lock to prevent concurrent scheduler runs."""
    global LOCK_FILE
    lock_path = get_project_root() / "data" / "scheduler.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        LOCK_FILE = open(lock_path, "w")
        fcntl.flock(LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
        LOCK_FILE.write(str(os.getpid()))
        LOCK_FILE.flush()
        return True
    except (IOError, OSError) as e:
        _logger.error("Could not acquire scheduler lock: %s", e)
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


def daemon_loop(config: dict):
    """Main daemon loop — runs collectors on schedule indefinitely."""
    scheduler_config = config.get("scheduler", {})
    groups = scheduler_config.get("groups", {})

    # Build interval map: collector_name → interval_minutes
    intervals = {}
    for group_def in groups.values():
        interval = group_def.get("interval_minutes", 360)
        for name in group_def.get("collectors", []):
            intervals[name] = interval

    if not intervals:
        _logger.error("No collectors configured in scheduler.groups")
        return

    _logger.info("Scheduler started: %d collectors across %d groups", len(intervals), len(groups))
    for name, interval in intervals.items():
        _logger.info("  %-25s every %d min", name, interval)

    # Track last run time per collector
    last_run = {}
    all_collector_names = list(intervals.keys())

    while not _shutdown.is_set():
        now = datetime.now(timezone.utc)

        # Find collectors that are due
        due = []
        for name in all_collector_names:
            interval_sec = intervals[name] * 60
            last = last_run.get(name)
            if last is None or (now - last).total_seconds() >= interval_sec:
                due.append(name)

        if due:
            _logger.info("── Tick: %d collectors due ──", len(due))
            results = run_group(due, config, scheduler_config)
            print_summary(results)

            for r in results:
                if r["status"] in ("success", "partial", "failed"):
                    last_run[r["name"]] = now

        # Sleep for 60 seconds before next tick
        _shutdown.wait(60)

    _logger.info("Scheduler shutting down gracefully")


# ── Signal Handling ───────────────────────────────────────

def _handle_shutdown(signum, frame):
    _logger.info("Received signal %s — initiating graceful shutdown", signum)
    _shutdown.set()


# ── Main ──────────────────────────────────────────────────

import os

def main():
    parser = argparse.ArgumentParser(description="Collector scheduler for Opportunity Intelligence Platform")
    parser.add_argument("--once", action="store_true", help="Run all collectors once and exit")
    parser.add_argument("--group", type=str, help="Run a specific group (fast/standard/daily)")
    parser.add_argument("--collector", type=str, help="Run a single collector by name")
    args = parser.parse_args()

    setup_logging()
    config = load_config()

    # Signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    _logger.info("Collector Scheduler — Opportunity Intelligence Platform")
    _logger.info("Project root: %s", get_project_root())

    # Acquire lock
    if not acquire_lock():
        sys.exit(1)

    try:
        if args.collector:
            # Run a single collector
            _logger.info("Running single collector: %s", args.collector)
            result = run_with_retry(args.collector, config)
            print_summary([result])
            sys.exit(0 if result["status"] in ("success", "partial") else 1)

        if args.group:
            # Run a specific group
            scheduler_config = config.get("scheduler", {})
            group_def = scheduler_config.get("groups", {}).get(args.group)
            if not group_def:
                _logger.error("Unknown group: %s. Available: %s", args.group,
                              list(scheduler_config.get("groups", {}).keys()))
                sys.exit(1)
            _logger.info("Running group: %s (%d collectors)", args.group, len(group_def.get("collectors", [])))
            results = run_group(group_def.get("collectors", []), config, scheduler_config)
            print_summary(results)
            has_failure = any(r["status"] == "failed" for r in results)
            sys.exit(1 if has_failure else 0)

        if args.once:
            # Run all groups once
            results = run_all_groups(config)
            print_summary(results)
            has_failure = any(r["status"] == "failed" for r in results)
            sys.exit(1 if has_failure else 0)

        # Default: daemon mode
        daemon_loop(config)

    finally:
        release_lock()


if __name__ == "__main__":
    main()
