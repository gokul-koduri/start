"""Collection agent — wraps existing data collectors into the agent pipeline."""

import logging
from pathlib import Path
import sys

from agents.base import AgentResult, BaseAgent

# Import all collectors from the existing registry
sys.path.insert(0, str(Path(__file__).parent.parent))
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

# Fast collectors suitable for daily runs
DAILY_COLLECTORS = ["google_news_rss", "techcrunch_rss"]

_logger = logging.getLogger(__name__)


class CollectionAgent(BaseAgent):
    """Agent that runs the existing data collectors.

    Config options:
        collectors: list of collector names to run (default: all)
        daily_collectors: subset for daily runs
        daily_mode: bool — if True, only run daily_collectors
    """

    @property
    def name(self) -> str:
        return "collection"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        daily_mode = self.config.get("daily_mode", False)

        # Determine which collectors to run
        if daily_mode:
            collector_names = self.config.get("daily_collectors", DAILY_COLLECTORS)
        else:
            collector_names = self.config.get("collectors", list(ALL_COLLECTORS.keys()))

        _logger.info("CollectionAgent: Running %d collectors (daily_mode=%s)",
                     len(collector_names), daily_mode)

        results = []
        total_collected = 0
        total_inserted = 0
        total_errors = []

        for collector_name in collector_names:
            if collector_name not in ALL_COLLECTORS:
                _logger.warning("Unknown collector: %s — skipping", collector_name)
                continue

            collector_class = ALL_COLLECTORS[collector_name]
            collector = collector_class(config={}, dry_run=self.dry_run)

            _logger.info("Running collector: %s", collector_name)
            result = collector.run()

            results.append({
                "name": collector_name,
                "status": result.status,
                "records_collected": result.records_collected,
                "records_inserted": result.records_inserted,
                "records_skipped": result.records_skipped,
                "errors": result.errors,
            })

            total_collected += result.records_collected
            total_inserted += result.records_inserted
            total_errors.extend(result.errors)

        overall_status = "success"
        if all(r["status"] == "failed" for r in results):
            overall_status = "failed"
        elif any(r["status"] == "failed" for r in results):
            overall_status = "partial"

        return AgentResult(
            agent_name=self.name,
            status=overall_status,
            data={
                "collectors_run": len(results),
                "total_collected": total_collected,
                "total_inserted": total_inserted,
                "records_affected": total_inserted,
                "collector_results": results,
            },
            errors=total_errors[:20],
        )
