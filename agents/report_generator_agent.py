"""Report Generator Agent — scheduled HTML/Markdown report generation + delivery.

Generates periodic reports from database contents:
- weekly_digest: new data summary, key metrics, alerts, LLM pricing changes
- monthly_deep_dive: full analysis with trends and recommendations (in full pipeline)

Output formats: Markdown (.md) and HTML (.html).
Optional email delivery to Pro/Enterprise license holders.

Runs in the weekly pipeline (after collection) and full pipeline.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema
from config import get_project_root
from utils.email_queue import (
    queue_bulk,
    get_active_recipients,
    render_template,
    plain_from_html,
)

_logger = logging.getLogger(__name__)


class ReportGeneratorAgent(BaseAgent):
    """Generates scheduled reports from database contents.

    Config options:
        output_dir: str — directory for generated reports (default: data/reports)
        output_formats: list[str] — formats to generate (default: ["markdown", "html"])
        email_delivery.enabled: bool — enable email delivery
        email_delivery.smtp_host: str — SMTP server
        email_delivery.smtp_port: int — SMTP port (default 587)
        email_delivery.smtp_user: str — SMTP username
        email_delivery.smtp_password: str — SMTP password
        email_delivery.from_address: str — sender email
    """

    @property
    def name(self) -> str:
        return "report_generator"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        pipeline_name = self.config.get("_pipeline_name", "weekly")
        output_dir = Path(get_project_root() / self.config.get("output_dir", "data/reports"))
        formats = self.config.get("output_formats", ["markdown", "html"])
        email_config = self.config.get("email_delivery", {})

        output_dir.mkdir(parents=True, exist_ok=True)

        _logger.info("ReportGeneratorAgent: Generating reports (pipeline=%s, formats=%s)", pipeline_name, formats)

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("ReportGeneratorAgent: Cannot connect to DB: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()

            # Determine report type based on pipeline
            if pipeline_name == "full":
                report_type = "monthly_deep_dive"
            else:
                report_type = "weekly_digest"

            # Render report content
            md_content = self._render_report(cursor, report_type, conn)
            records = len(md_content)

            generated_files = []
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

            for fmt in formats:
                if fmt == "markdown":
                    file_path = output_dir / f"{report_type}_{now_str}.md"
                    file_path.write_text(md_content, encoding="utf-8")
                    generated_files.append(str(file_path))
                    _logger.info("ReportGeneratorAgent: Saved %s", file_path)

                elif fmt == "html":
                    html_content = self._convert_to_html(md_content)
                    file_path = output_dir / f"{report_type}_{now_str}.html"
                    file_path.write_text(html_content, encoding="utf-8")
                    generated_files.append(str(file_path))
                    _logger.info("ReportGeneratorAgent: Saved %s", file_path)

            # Log to generated_reports table
            for fpath in generated_files:
                fmt_name = "html" if fpath.endswith(".html") else "markdown"
                cursor.execute(
                    """INSERT INTO generated_reports (report_type, format, file_path,
                       status, record_count, generated_at)
                       VALUES (%s, %s, %s, 'success', %s, %s)""",
                    (report_type, fmt_name, fpath, records,
                     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
                )

            # Queue email delivery (sent asynchronously by email_worker)
            sent_to = []
            if email_config.get("enabled"):
                sent_to = self._queue_report_email(md_content, report_type, now_str)
                cursor.execute(
                    """INSERT INTO generated_reports (report_type, format, file_path,
                       sent_to, status, record_count, generated_at)
                       VALUES (%s, 'email', '', %s, 'success', %s, %s)""",
                    (report_type, json.dumps(sent_to), records,
                     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
                )

            conn.commit()

            _logger.info(
                "ReportGeneratorAgent: Done — %d files, %d email recipients",
                len(generated_files), len(sent_to),
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "report_type": report_type,
                    "files_generated": generated_files,
                    "emails_sent": len(sent_to),
                    "records_affected": len(generated_files),
                },
            )

        except Exception as e:
            _logger.error("ReportGeneratorAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

    # ── Report rendering ──

    def _render_report(self, cursor, report_type: str, conn) -> str:
        """Render the full report as Markdown."""
        now = datetime.now(timezone.utc)
        lines = []

        if report_type == "weekly_digest":
            lines.extend(self._section_header(cursor, "Weekly Digest", now))
            lines.extend(self._section_data_summary(cursor))
            lines.extend(self._section_top_failures(cursor))
            lines.extend(self._section_llm_updates(cursor))
            lines.extend(self._section_active_alerts(cursor))
            lines.extend(self._section_collection_health(cursor))

        elif report_type == "monthly_deep_dive":
            lines.extend(self._section_header(cursor, "Monthly Deep Dive", now))
            lines.extend(self._section_data_summary(cursor))
            lines.extend(self._section_top_failures(cursor))
            lines.extend(self._section_failure_trends(cursor))
            lines.extend(self._section_survival_rates(cursor))
            lines.extend(self._section_llm_portfolio(cursor))
            lines.extend(self._section_llm_updates(cursor))
            lines.extend(self._section_active_alerts(cursor))
            lines.extend(self._section_revival_opportunities(cursor))
            lines.extend(self._section_recommendations(cursor))

        return "\n".join(lines)

    def _section_header(self, cursor, title: str, now: datetime) -> list[str]:
        """Report header with date and data counts."""
        cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
        startup_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
        news_count = cursor.fetchone()["cnt"]

        return [
            f"# {title}",
            f"",
            f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"**Database:** {startup_count:,} failed startups | {news_count:,} news articles",
            f"",
            "---",
            f"",
        ]

    def _section_data_summary(self, cursor) -> list[str]:
        """Data collection summary — recent additions."""
        lines = ["## Data Summary", ""]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM failed_startups WHERE collected_at >= %s", (cutoff,))
        new_startups = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM news_articles WHERE collected_at >= %s", (cutoff,))
        new_articles = cursor.fetchone()["cnt"]

        lines.append(f"- **New startups (7d):** {new_startups:,}")
        lines.append(f"- **New articles (7d):** {new_articles:,}")
        lines.append("")

        # Top sectors by new entries
        cursor.execute(
            """SELECT sector, COUNT(*) as cnt FROM failed_startups
               WHERE collected_at >= %s GROUP BY sector ORDER BY cnt DESC LIMIT 5""",
            (cutoff,),
        )
        sectors = cursor.fetchall()
        if sectors:
            lines.append("**Top sectors (new):**")
            for s in sectors:
                lines.append(f"  - {s['sector'] or 'Unknown'}: {s['cnt']}")
            lines.append("")

        return lines

    def _section_top_failures(self, cursor) -> list[str]:
        """Top failure reasons."""
        lines = ["## Top Failure Reasons", ""]

        cursor.execute(
            """SELECT failure_category, COUNT(*) as cnt FROM failed_startups
               WHERE failure_category IS NOT NULL
               GROUP BY failure_category ORDER BY cnt DESC LIMIT 10"""
        )
        categories = cursor.fetchall()
        for c in categories:
            lines.append(f"- **{c['failure_category']}**: {c['cnt']} startups")
        lines.append("")
        return lines

    def _section_failure_trends(self, cursor) -> list[str]:
        """Year-over-year failure trends."""
        lines = ["## Failure Trends by Year", ""]

        cursor.execute(
            """SELECT year_shutdown, COUNT(*) as cnt FROM failed_startups
               WHERE year_shutdown IS NOT NULL
               GROUP BY year_shutdown ORDER BY year_shutdown DESC LIMIT 10"""
        )
        years = cursor.fetchall()
        lines.append("| Year | Failures |")
        lines.append("|------|----------|")
        for y in years:
            lines.append(f"| {y['year_shutdown']} | {y['cnt']:,} |")
        lines.append("")
        return lines

    def _section_survival_rates(self, cursor) -> list[str]:
        """BLS survival rate highlights."""
        lines = ["## Survival Rate Highlights", ""]
        cursor.execute(
            """SELECT industry_name, year, age_1_yr_survival, age_5_yr_survival
               FROM bls_survival_rates
               WHERE naics_code = '31'
               ORDER BY year DESC LIMIT 5"""
        )
        rows = cursor.fetchall()
        if rows:
            lines.append("| Industry | Year | 1-Year | 5-Year |")
            lines.append("|----------|------|--------|--------|")
            for r in rows:
                lines.append(
                    f"| {r['industry_name']} | {r['year']} | "
                    f"{r['age_1_yr_survival']:.1f}% | {r['age_5_yr_survival']:.1f}% |"
                )
            lines.append("")
        else:
            lines.append("*No BLS survival data available.*\n")
        return lines

    def _section_llm_updates(self, cursor) -> list[str]:
        """LLM pricing changes and portfolio updates."""
        lines = ["## LLM Infrastructure Updates", ""]

        cursor.execute(
            """SELECT provider, model_name, input_change_pct, output_change_pct, detected_at
               FROM llm_price_changes
               ORDER BY detected_at DESC LIMIT 5"""
        )
        changes = cursor.fetchall()
        if changes:
            lines.append("### Recent Price Changes")
            lines.append("")
            for c in changes:
                direction = "decrease" if c["input_change_pct"] < 0 else "increase"
                lines.append(
                    f"- **{c['model_name']}** ({c['provider']}): "
                    f"input {direction}d {abs(c['input_change_pct']):.1f}%, "
                    f"output {direction}d {abs(c['output_change_pct']):.1f}%"
                )
            lines.append("")

        # Current portfolio allocation
        cursor.execute(
            """SELECT task_category, provider, model_name, allocation_pct, composite_score
               FROM llm_portfolio ORDER BY task_category, rank_position LIMIT 15"""
        )
        portfolio = cursor.fetchall()
        if portfolio:
            lines.append("### Portfolio Allocation")
            lines.append("")
            lines.append("| Task | Model | Provider | Allocation | Score |")
            lines.append("|------|-------|----------|------------|-------|")
            for p in portfolio:
                lines.append(
                    f"| {p['task_category']} | {p['model_name']} | "
                    f"{p['provider']} | {p['allocation_pct']:.0f}% | "
                    f"{p['composite_score'] or 'N/A'} |"
                )
            lines.append("")

        return lines

    def _section_llm_portfolio(self, cursor) -> list[str]:
        """Extended LLM portfolio analysis for monthly reports."""
        lines = ["## LLM Portfolio Analysis", ""]
        return self._section_llm_updates(cursor)

    def _section_active_alerts(self, cursor) -> list[str]:
        """Active optimization alerts."""
        lines = ["## Active Alerts", ""]
        cursor.execute(
            """SELECT alert_type, title, priority, estimated_savings_pct, created_at
               FROM llm_optimization_alerts
               WHERE dismissed = 0
               ORDER BY priority DESC, created_at DESC LIMIT 10"""
        )
        alerts = cursor.fetchall()
        if alerts:
            for a in alerts:
                savings = f" (~{a['estimated_savings_pct']:.0f}% savings)" if a["estimated_savings_pct"] else ""
                lines.append(f"- **[{a['priority'].upper()}]** {a['title']}{savings}")
            lines.append("")
        else:
            lines.append("*No active alerts.*\n")
        return lines

    def _section_collection_health(self, cursor) -> list[str]:
        """Data collection health check."""
        lines = ["## Collection Health", ""]

        cursor.execute(
            """SELECT collector_name, started_at, status, records_collected
               FROM collection_runs ORDER BY started_at DESC LIMIT 10"""
        )
        runs = cursor.fetchall()
        for r in runs:
            status_icon = "OK" if r["status"] == "success" else "WARN"
            lines.append(
                f"- [{status_icon}] {r['collector_name']}: "
                f"{r['records_collected']} records ({r['started_at']})"
            )
        lines.append("")
        return lines

    def _section_revival_opportunities(self, cursor) -> list[str]:
        """Revival opportunity highlights."""
        lines = ["## Revival Opportunities", ""]

        cursor.execute(
            """SELECT industry, why_returning, market_fit, key_investors
               FROM revival_industries LIMIT 5"""
        )
        rows = cursor.fetchall()
        for r in rows:
            lines.append(f"### {r['industry']}")
            lines.append(f"Why returning: {r['why_returning']}")
            if r.get("key_investors"):
                lines.append(f"Key investors: {r['key_investors']}")
            lines.append("")
        return lines

    def _section_recommendations(self, cursor) -> list[str]:
        """Actionable recommendations based on data analysis."""
        lines = ["## Recommendations", ""]
        lines.append("1. **Monitor LLM pricing trends** — Review active alerts for cost optimization opportunities.")
        lines.append("2. **Track emerging sectors** — Check weekly digest for new failure patterns in emerging industries.")
        lines.append("3. **Review data freshness** — Ensure RSS collectors are running on schedule.")
        lines.append("")
        return lines

    # ── HTML conversion ──

    def _convert_to_html(self, md_content: str) -> str:
        """Convert Markdown report to styled HTML using the markdown library."""
        try:
            import markdown as md_lib
            html_body = md_lib.markdown(md_content, extensions=["tables", "fenced_code"])
        except ImportError:
            _logger.warning("ReportGeneratorAgent: markdown library not found, using basic conversion")
            html_body = md_content.replace("\n", "<br>\n")

        return (
            "<!DOCTYPE html>\n"
            "<html lang='en'>\n<head>\n"
            "<meta charset='UTF-8'>\n"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
            f"<title>Startup Research Report</title>\n"
            "<style>\n"
            "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; "
            "max-width: 900px; margin: 0 auto; padding: 2rem; color: #1a1a2e; background: #fafafa; }\n"
            "  h1 { color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 0.5rem; }\n"
            "  h2 { color: #16213e; margin-top: 2rem; }\n"
            "  h3 { color: #0f3460; }\n"
            "  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }\n"
            "  th, td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }\n"
            "  th { background: #0f3460; color: white; }\n"
            "  tr:nth-child(even) { background: #f5f5f5; }\n"
            "  code { background: #e8e8e8; padding: 0.15rem 0.4rem; border-radius: 3px; }\n"
            "  hr { border: none; border-top: 1px solid #ddd; margin: 2rem 0; }\n"
            "</style>\n"
            "</head>\n<body>\n"
            f"{html_body}\n"
            "</body>\n</html>"
        )

    # ── Email delivery (queued) ──

    def _queue_report_email(self, md_content: str,
                             report_type: str, now_str: str) -> list[str]:
        """Queue report email for Pro/Enterprise users. Sent asynchronously by email_worker."""
        try:
            recipients = get_active_recipients()
            emails = [r["email"] for r in recipients if r.get("email")]
        except Exception:
            emails = []

        if not emails:
            _logger.info("ReportGeneratorAgent: No active recipients for email delivery")
            return []

        # Build HTML using the report template (falls back to _convert_to_html)
        try:
            html_content = render_template("report.html", {
                "header_title": report_type.replace("_", " ").title(),
                "header_subtitle": now_str,
                "intro_text": f"Here is your {report_type.replace('_', ' ')} from the Opportunity Intelligence Platform.",
                "sections": [],  # sections rendered from markdown below
                "dashboard_url": "https://github.com/gokul-koduri/start",
                "unsubscribe_url": "https://github.com/gokul-koduri/start#email-preferences",
                "preferences_url": "https://github.com/gokul-koduri/start#email-preferences",
            })
        except Exception:
            html_content = self._convert_to_html(md_content)

        subject = f"[OIP] {report_type.replace('_', ' ').title()} — {now_str}"

        try:
            queued_ids = queue_bulk(
                emails,
                subject=subject,
                email_type="report",
                plain_body=md_content,
                html_body=html_content,
                priority=5,
                related_id=report_type,
                metadata={"report_type": report_type, "generated_at": now_str},
            )
            _logger.info(
                "ReportGeneratorAgent: Queued %d report emails (type=%s)",
                len(queued_ids), report_type,
            )
            return emails
        except Exception as e:
            _logger.error("ReportGeneratorAgent: Email queue failed: %s", e)
            return []
