"""Report agent — wraps the report generator into the agent pipeline."""

import logging

from agents.base import AgentResult, BaseAgent
from config import get_project_root, load_config
from db.connection import get_connection
from db import schema
from report.generator import generate_report

_logger = logging.getLogger(__name__)


class ReportAgent(BaseAgent):
    """Agent that generates the markdown research report.

    Config options:
        output_path: filename for the report (default from settings)
        only_on_new_data: if True, skip when no new records were collected
    """

    @property
    def name(self) -> str:
        return "report"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        config = load_config()
        report_config = config.get("report", {})
        agents_config = self.config

        output_filename = agents_config.get(
            "output_path",
            report_config.get(
                "output_path", "Failed_Startups_Manufacturing_Revival_Report.md"
            ),
        )
        output_path = get_project_root() / output_filename

        # Check if we should skip due to no new data
        only_on_new_data = agents_config.get("only_on_new_data", True)
        if only_on_new_data and upstream_results:
            collection_result = _find_agent_result(upstream_results, "collection")
            if (
                collection_result
                and collection_result.data.get("total_inserted", 0) == 0
            ):
                _logger.info(
                    "ReportAgent: No new data collected — skipping report generation"
                )
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"skipped": True, "reason": "no_new_data"},
                )

        _logger.info("ReportAgent: Generating report → %s", output_path)

        conn = get_connection()
        try:
            schema.init_schema(conn)
            generate_report(conn, config, str(output_path))
        finally:
            conn.close()

        # Read back stats
        file_size = output_path.stat().st_size if output_path.exists() else 0
        content = output_path.read_text() if output_path.exists() else ""
        section_count = content.count("\n## ")

        _logger.info(
            "ReportAgent: Report generated (%d bytes, %d sections)",
            file_size,
            section_count,
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "report_path": str(output_path),
                "report_filename": output_filename,
                "report_size_bytes": file_size,
                "sections": section_count,
                "records_affected": 1,
            },
        )


def _find_agent_result(results: list, agent_name: str):
    """Find an AgentResult by agent_name in the upstream results list."""
    for r in results:
        if hasattr(r, "agent_name") and r.agent_name == agent_name:
            return r
    return None
