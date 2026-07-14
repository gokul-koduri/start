"""Span Agent — unified pipeline control, health monitoring, and research interface.

Combines three capabilities:
- Task 2: Pipeline execution and monitoring
- Task 3: Report generation (research reports)
- Task 4: AI research queries (natural language)

Runs after every pipeline execution (daily, weekly, full).
Prints a health report with actionable suggestions to stdout.

Unified CLI usage:
    python run_agent.py --span run --pipeline daily
    python run_agent.py --span status
    python run_agent.py --span ask "What are the top 5 manufacturing revival opportunities?"
    python run_agent.py --span report --type opportunity --topic "Ohio EV Battery"
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema
from config import get_project_root

_logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class PipelineRun:
    """Represents a pipeline execution with span tracking."""
    pipeline_name: str
    started_at: datetime
    status: str = "running"
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    records_collected: int = 0
    records_analyzed: int = 0
    cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    anomalies: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pipeline_name": self.pipeline_name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "records_collected": self.records_collected,
            "records_analyzed": self.records_analyzed,
            "cost_usd": self.cost_usd,
            "error_count": len(self.errors),
            "anomaly_count": len(self.anomalies),
        }


@dataclass
class ResearchReport:
    """Template for research reports."""
    title: str
    template_type: str  # opportunity_report, market_viability, startup_success
    topic: str
    sections: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class SpanAgent(BaseAgent):
    """Pipeline health monitor with anomaly detection.

    Config options:
        lookback_days: int — days of history to analyze (default: 7)
        anomaly_thresholds.duration_multiplier: float — slow_run threshold (default: 2.0)
        anomaly_thresholds.failure_rate_pct: float — high_failure threshold (default: 10.0)
        anomaly_thresholds.data_drop_pct: float — data_drop threshold (default: 50.0)
    """

    @property
    def name(self) -> str:
        return "span_monitor"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        pipeline_name = self.config.get("_pipeline_name", "daily")
        lookback_days = self.config.get("lookback_days", 7)
        thresholds = self.config.get("anomaly_thresholds", {})
        duration_mult = thresholds.get("duration_multiplier", 2.0)
        failure_rate = thresholds.get("failure_rate_pct", 10.0)
        data_drop_pct = thresholds.get("data_drop_pct", 50.0)

        _logger.info(
            "SpanAgent: Analyzing pipeline '%s' health (lookback=%dd)",
            pipeline_name,
            lookback_days,
        )

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("SpanAgent: Cannot connect to DB: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()
            anomalies_found = 0
            snapshots_inserted = 0

            # Fetch recent agent runs
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=lookback_days)
            ).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """SELECT pipeline_name, agent_name, started_at, completed_at,
                          status, records_affected, error_message
                   FROM agent_runs
                   WHERE started_at >= %s AND pipeline_name = %s
                   ORDER BY started_at ASC""",
                (cutoff, pipeline_name),
            )
            runs = [dict(r) for r in cursor.fetchall()]

            # Also include all pipelines if specific pipeline has no runs
            if not runs:
                cursor.execute(
                    """SELECT pipeline_name, agent_name, started_at, completed_at,
                              status, records_affected, error_message
                       FROM agent_runs
                       WHERE started_at >= %s
                       ORDER BY started_at ASC""",
                    (cutoff,),
                )
                runs = [dict(r) for r in cursor.fetchall()]

            if not runs:
                _logger.info("SpanAgent: No agent runs in lookback window")
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"anomalies": 0, "snapshots": 0, "records_affected": 0},
                )

            # Group by agent_name
            agent_runs = defaultdict(list)
            for run in runs:
                agent_runs[run["agent_name"]].append(run)

            # Analyze each agent
            health_report = []
            suggestions = []

            for agent_name, agent_history in sorted(agent_runs.items()):
                # Compute duration from timestamps
                durations = []
                statuses = []
                records = []

                for run in agent_history:
                    dur = self._parse_duration(
                        run.get("started_at"), run.get("completed_at")
                    )
                    if dur is not None:
                        durations.append(dur)
                    statuses.append(run.get("status", "unknown"))
                    records.append(run.get("records_affected", 0))

                if not durations:
                    continue

                avg_duration = sum(durations) / len(durations)
                failure_count = sum(1 for s in statuses if s == "failed")
                failure_pct = (failure_count / len(statuses)) * 100 if statuses else 0
                avg_records = sum(records) / len(records) if records else 0
                last_run = agent_history[-1]
                last_status = last_run.get("status", "unknown")
                last_duration = durations[-1] if durations else 0
                last_records = records[-1] if records else 0

                # Anomaly: slow run
                anomaly_type = None
                anomaly_detail = None

                if len(durations) >= 2 and last_duration > avg_duration * duration_mult:
                    ratio = last_duration / avg_duration if avg_duration > 0 else 0
                    anomaly_type = "slow_run"
                    anomaly_detail = f"Duration {ratio:.1f}x average ({last_duration:.1f}s vs {avg_duration:.1f}s avg)"
                    suggestions.append(
                        f"  [SLOW] {agent_name}: {anomaly_detail}. "
                        f"Check for external API latency or resource contention."
                    )

                # Anomaly: high failure rate
                if failure_pct > failure_rate and len(statuses) >= 3:
                    anomaly_type = anomaly_type or "high_failure"
                    anomaly_detail = (
                        anomaly_detail
                        or f"Failure rate {failure_pct:.1f}% ({failure_count}/{len(statuses)})"
                    )
                    suggestions.append(
                        f"  [FAIL] {agent_name}: {anomaly_detail}. "
                        f"Review error logs and check data source availability."
                    )

                # Anomaly: data drop
                if len(records) >= 2:
                    prev_records = records[-2] if records[-2] > 0 else 1
                    drop_pct = ((prev_records - last_records) / prev_records) * 100
                    if drop_pct > data_drop_pct:
                        anomaly_type = anomaly_type or "data_drop"
                        anomaly_detail = (
                            anomaly_detail
                            or f"Records dropped {drop_pct:.0f}% ({prev_records} -> {last_records})"
                        )
                        suggestions.append(
                            f"  [DROP] {agent_name}: {anomaly_detail}. "
                            f"Verify data source hasn't changed format or rate-limited."
                        )

                # Health score
                health_score = self._compute_health(
                    avg_duration, last_duration, failure_pct, last_records
                )

                # Health report entry
                health_report.append(
                    {
                        "agent": agent_name,
                        "runs": len(agent_history),
                        "avg_duration": avg_duration,
                        "last_duration": last_duration,
                        "failure_pct": failure_pct,
                        "avg_records": avg_records,
                        "health": health_score,
                        "anomaly": anomaly_type,
                    }
                )

                # Insert snapshot
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """INSERT INTO span_snapshots
                       (pipeline_name, agent_name, duration_seconds, records_affected,
                        status, anomaly_detected, anomaly_type, anomaly_detail, snapshot_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        pipeline_name,
                        agent_name,
                        last_duration,
                        last_records,
                        last_status,
                        1 if anomaly_type else 0,
                        anomaly_type,
                        anomaly_detail,
                        now,
                    ),
                )
                snapshots_inserted += 1
                if anomaly_type:
                    anomalies_found += 1

            conn.commit()

            # Print health report
            self._print_health_report(health_report, suggestions)

            _logger.info(
                "SpanAgent: Done — %d agents analyzed, %d anomalies, %d snapshots",
                len(health_report),
                anomalies_found,
                snapshots_inserted,
            )

            return AgentResult(
                agent_name=self.name,
                status="success" if anomalies_found == 0 else "partial",
                data={
                    "agents_analyzed": len(health_report),
                    "anomalies_found": anomalies_found,
                    "snapshots_inserted": snapshots_inserted,
                    "health_report": health_report,
                    "suggestions": suggestions,
                    "records_affected": snapshots_inserted,
                },
                errors=[f"{anomalies_found} anomalies detected"]
                if anomalies_found
                else [],
            )

        except Exception as e:
            _logger.error("SpanAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

    def _parse_duration(
        self, started_at: str | None, completed_at: str | None
    ) -> float | None:
        """Parse duration from timestamp strings."""
        if not started_at or not completed_at:
            return None
        try:
            fmt = "%Y-%m-%d %H:%M:%S"
            start = datetime.strptime(started_at, fmt)
            end = datetime.strptime(completed_at, fmt)
            delta = (end - start).total_seconds()
            return max(0, delta)
        except ValueError:
            return None

    def _compute_health(
        self, avg_dur: float, last_dur: float, failure_pct: float, records: int
    ) -> str:
        """Compute a simple health score: green, yellow, or red."""
        if failure_pct > 20:
            return "red"
        if failure_pct > 10:
            return "yellow"
        if avg_dur > 0 and last_dur > avg_dur * 2.5:
            return "yellow"
        if records == 0 and failure_pct == 0:
            return "yellow"
        return "green"

    def _print_health_report(self, report: list[dict], suggestions: list[str]):
        """Print a formatted health report to stdout."""
        if not report:
            print("\n  SpanAgent: No agent runs to analyze.")
            return

        print(f"\n{'='*60}")
        print("  PIPELINE HEALTH REPORT")
        print(f"{'='*60}")
        print(
            f"  {'Agent':<25} {'Runs':>4} {'Avg(s)':>7} {'Last(s)':>7} {'Fail%':>6} {'Health':>7}"
        )
        print(f"  {'-'*25} {'-'*4} {'-'*7} {'-'*7} {'-'*6} {'-'*7}")

        for entry in report:
            health_icon = {"green": "OK", "yellow": "WARN", "red": "FAIL"}.get(
                entry["health"], "?"
            )
            anomaly_flag = " !" if entry["anomaly"] else ""
            print(
                f"  {entry['agent']:<25} {entry['runs']:>4} "
                f"{entry['avg_duration']:>7.1f} {entry['last_duration']:>7.1f} "
                f"{entry['failure_pct']:>5.1f}% {health_icon:>7}{anomaly_flag}"
            )

        if suggestions:
            print("\n  SUGGESTIONS:")
            for s in suggestions:
                print(s)

        print(f"\n{'='*60}\n")

    # ══════════════════════════════════════════════════════════════════════════
    # Task 2: Pipeline Control Methods
    # ══════════════════════════════════════════════════════════════════════════

    def run_pipeline(self, pipeline_name: str = "daily") -> AgentResult:
        """Execute a named pipeline (collection, analysis, report, full)."""
        _logger.info("SpanAgent: Running pipeline '%s'", pipeline_name)

        from agents.orchestrator import OrchestratorAgent

        config = self.config.copy()
        config["_pipeline_name"] = pipeline_name
        config["_scheduled"] = False
        config["dry_run"] = False

        # Merge agent-specific configs
        config.update(self.config.get("agents", {}))

        orchestrator = OrchestratorAgent(config=config, dry_run=False)
        result = orchestrator.run()

        # Track the pipeline run in span_snapshots
        self._log_pipeline_run(pipeline_name, result)

        return result

    def trigger_collection(self, collectors: list[str] | None = None) -> AgentResult:
        """Trigger data collection runs."""
        _logger.info("SpanAgent: Triggering collection (collectors=%s)", collectors)

        # Import here to avoid circular imports
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from run_collectors import run_collectors

        try:
            args = type("Args", (), {
                "all": collectors is None,
                "collector": collectors[0] if collectors else None,
                "collectors": collectors or [],
                "dry_run": self.dry_run,
                "force": True,
            })()

            result_count = run_collectors(args)

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"collectors_run": collectors or "all", "records_collected": result_count},
            )
        except Exception as e:
            _logger.error("SpanAgent: Collection failed: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )

    def get_pipeline_status(self) -> dict[str, Any]:
        """Get current pipeline health metrics and status."""
        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            # Recent snapshots
            cursor.execute(
                """SELECT pipeline_name, agent_name, duration_seconds, records_affected,
                          status, anomaly_detected, anomaly_type, snapshot_at
                   FROM span_snapshots
                   ORDER BY snapshot_at DESC LIMIT 100"""
            )
            snapshots = [dict(r) for r in cursor.fetchall()]

            # Recent agent runs
            cursor.execute(
                """SELECT pipeline_name, agent_name, started_at, completed_at,
                          status, records_affected, error_message
                   FROM agent_runs
                   ORDER BY started_at DESC LIMIT 50"""
            )
            runs = [dict(r) for r in cursor.fetchall()]

            # Cost tracking (optional table)
            try:
                cursor.execute(
                    """SELECT SUM(cost_usd) as total_cost, COUNT(*) as run_count
                       FROM ollama_usage ORDER BY tracked_at DESC LIMIT 1"""
                )
                cost_row = cursor.fetchone()
            except Exception:
                cost_row = None

            cursor.close()
            conn.close()

            return {
                "healthy": len([s for s in snapshots if not s.get("anomaly_detected")]) / max(len(snapshots), 1),
                "snapshots": snapshots[:20],
                "recent_runs": runs[:10],
                "total_cost": cost_row.get("total_cost", 0) if cost_row else 0,
                "run_count": cost_row.get("run_count", 0) if cost_row else 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            _logger.error("SpanAgent: Status check failed: %s", e)
            return {"error": str(e)}

    def _log_pipeline_run(self, pipeline_name: str, result: AgentResult) -> None:
        """Log pipeline run to span_snapshots table."""
        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO span_snapshots
                   (pipeline_name, agent_name, duration_seconds, records_affected,
                    status, anomaly_detected, anomaly_type, anomaly_detail, snapshot_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    pipeline_name,
                    "pipeline_run",
                    result.data.get("elapsed_seconds", 0),
                    result.data.get("records_affected", 0),
                    result.status,
                    1 if result.errors else 0,
                    "pipeline_failure" if result.errors else None,
                    "; ".join(result.errors[:3]) if result.errors else None,
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            _logger.error("SpanAgent: Failed to log pipeline run: %s", e)

    # ══════════════════════════════════════════════════════════════════════════
    # Task 3: Report Generation Methods
    # ══════════════════════════════════════════════════════════════════════════

    def generate_research_report(
        self,
        template_type: str = "opportunity_report",
        topic: str = "",
        custom_sections: list[dict] | None = None,
    ) -> AgentResult:
        """Generate a research report from template.

        Template types:
        - opportunity_report: Manufacturing revival opportunities
        - market_viability_report: Global market analysis
        - startup_success_report: Success pattern analysis
        """
        _logger.info(
            "SpanAgent: Generating research report (type=%s, topic=%s)",
            template_type,
            topic,
        )

        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()
        except Exception as e:
            _logger.error("SpanAgent: Cannot connect to DB: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            # Build report content based on template
            report = self._build_report_template(
                cursor, template_type, topic, custom_sections or []
            )

            # Save report file
            output_dir = Path(get_project_root()) / "data" / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)

            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            safe_topic = topic.replace(" ", "_")[:30] if topic else template_type
            file_path = output_dir / f"{safe_topic}_{now_str}.md"
            file_path.write_text(report["content"], encoding="utf-8")

            # Log to database
            cursor.execute(
                """INSERT INTO generated_reports (report_type, format, file_path,
                   status, record_count, generated_at)
                   VALUES (%s, 'markdown', %s, 'success', %s, %s)""",
                (
                    template_type,
                    str(file_path),
                    len(report["content"]),
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()

            _logger.info(
                "SpanAgent: Report generated: %s (%d chars)",
                file_path,
                len(report["content"]),
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "report_type": template_type,
                    "topic": topic,
                    "file_path": str(file_path),
                    "sections_count": len(report["sections"]),
                    "records_affected": len(report["content"]),
                },
            )
        except Exception as e:
            _logger.error("SpanAgent: Report generation failed: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
        finally:
            conn.close()

    def add_report_section(
        self, report_content: str, section_name: str, section_content: str
    ) -> str:
        """Add a custom section to existing report content.

        Inserts section before recommendations or at the end.
        """
        section_markdown = f"\n## {section_name}\n\n{section_content}\n"

        if "## Recommendations" in report_content:
            return report_content.replace(
                "## Recommendations",
                f"{section_markdown}\n## Recommendations",
            )
        return report_content + section_markdown

    def _build_report_template(
        self,
        cursor,
        template_type: str,
        topic: str,
        custom_sections: list[dict],
    ) -> dict:
        """Build report content from template type."""
        now = datetime.now(timezone.utc)
        lines = []

        if template_type == "opportunity_report":
            lines.extend(self._section_opportunity_header(topic, now))
            lines.extend(self._section_opportunity_summary(cursor))
            lines.extend(self._section_revival_opportunities(cursor))
            lines.extend(self._section_market_analysis(cursor))
            lines.extend(self._section_recommendations(cursor))

        elif template_type == "market_viability_report":
            lines.extend(self._section_market_header(topic, now))
            lines.extend(self._section_sector_analysis(cursor))
            lines.extend(self._section_geographic_analysis(cursor))
            lines.extend(self._section_viability_scores(cursor))

        elif template_type == "startup_success_report":
            lines.extend(self._section_success_header(topic, now))
            lines.extend(self._section_success_patterns(cursor))
            lines.extend(self._section_survival_rates(cursor))
            lines.extend(self._section_growth_factors(cursor))

        else:
            # Default template
            lines.extend(self._section_generic_header(topic, now))
            lines.extend(self._section_data_summary(cursor))

        # Add custom sections
        for section in custom_sections:
            lines.extend([f"\n## {section.get('name', 'Custom Section')}", ""])
            lines.extend(section.get("content", []))

        return {
            "content": "\n".join(lines),
            "sections": [template_type] + [s.get("name") for s in custom_sections],
        }

    def _section_opportunity_header(self, topic: str, now: datetime) -> list[str]:
        return [
            f"# {topic or 'Manufacturing Opportunity Intelligence Report'}",
            "",
            f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "> **Mission:** Which manufacturing companies should we build — and why?",
            "",
            "---",
            "",
        ]

    def _section_opportunity_summary(self, cursor) -> list[str]:
        """Summarize key opportunity metrics."""
        lines = ["## Executive Summary", ""]

        cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
        total_startups = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM revival_industries")
        revival_count = cursor.fetchone()["cnt"]

        lines.append(f"- **Total startups analyzed:** {total_startups:,}")
        lines.append(f"- **Revival opportunities identified:** {revival_count:,}")
        lines.append("")
        return lines

    def _section_revival_opportunities(self, cursor) -> list[str]:
        """Revival opportunities section."""
        lines = ["## Revival Opportunities", ""]

        cursor.execute(
            """SELECT industry, why_returning, market_fit, key_investors, market_size_2030
               FROM revival_industries ORDER BY market_size_2030 DESC LIMIT 10"""
        )
        rows = cursor.fetchall()

        if not rows:
            return ["*No revival opportunities data available.*", ""]

        for r in rows:
            lines.append(f"### {r['industry']}")
            if r.get("why_returning"):
                lines.append(f"**Why returning:** {r['why_returning']}")
            if r.get("market_fit"):
                lines.append(f"**Market fit:** {r['market_fit']}")
            if r.get("key_investors"):
                lines.append(f"**Key investors:** {r['key_investors']}")
            if r.get("market_size_2030"):
                lines.append(f"**TAM 2030:** ${r['market_size_2030']:,.0f}")
            lines.append("")

        return lines

    def _section_market_analysis(self, cursor) -> list[str]:
        """Market analysis section."""
        lines = ["## Market Analysis", ""]

        cursor.execute(
            """SELECT sector, COUNT(*) as cnt FROM failed_startups
               WHERE sector IS NOT NULL GROUP BY sector ORDER BY cnt DESC LIMIT 5"""
        )
        sectors = cursor.fetchall()

        if sectors:
            lines.append("### Top Sectors by Failure Count")
            for s in sectors:
                lines.append(f"- **{s['sector']}**: {s['cnt']} failures")
            lines.append("")

        return lines

    def _section_recommendations(self, cursor) -> list[str]:
        """Actionable recommendations."""
        lines = ["## Recommendations", ""]
        lines.append("1. **Monitor market timing** — Policy windows and demand signals change rapidly.")
        lines.append("2. **Validate CAPEX estimates** — Model-based estimates require supplier validation.")
        lines.append("3. **Focus on supply chain gaps** — Sectors with weak domestic supply = highest opportunity.")
        lines.append("")
        return lines

    # Market viability report sections
    def _section_market_header(self, topic: str, now: datetime) -> list[str]:
        return [
            f"# {topic or 'Global Market Viability Report'}",
            "",
            f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "---",
            "",
        ]

    def _section_sector_analysis(self, cursor) -> list[str]:
        lines = ["## Sector Analysis", ""]
        cursor.execute(
            """SELECT analysis_type, SUBSTRING(insights_json, 1, 500) as insights
               FROM analysis_global_market_viability LIMIT 5"""
        )
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                lines.append(f"### {r['analysis_type']}")
                lines.append(r.get("insights", "No data"))
                lines.append("")
        return lines

    def _section_geographic_analysis(self, cursor) -> list[str]:
        lines = ["## Geographic Analysis", ""]
        cursor.execute("SELECT region, closed_facility_types, revival_potential FROM geographic_hotspots LIMIT 10")
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                lines.append(f"- **{r['region']}**: {r.get('revival_potential', 'Unknown')}")
            lines.append("")
        return lines

    def _section_viability_scores(self, cursor) -> list[str]:
        lines = ["## Viability Scores", ""]
        cursor.execute("SELECT COUNT(*) as cnt FROM global_market_viability")
        count = cursor.fetchone()
        lines.append(f"Total evaluations: {count['cnt'] if count else 0}")
        lines.append("")
        return lines

    # Success report sections
    def _section_success_header(self, topic: str, now: datetime) -> list[str]:
        return [
            f"# {topic or 'Startup Success Patterns Report'}",
            "",
            f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "---",
            "",
        ]

    def _section_success_patterns(self, cursor) -> list[str]:
        lines = ["## Key Success Patterns", ""]
        cursor.execute(
            """SELECT failure_idea_patterns.idea_category,
                      GROUP_CONCAT(DISTINCT failed_startups.name SEPARATOR ', ') as examples
               FROM failure_idea_patterns
               LEFT JOIN failed_startups ON failed_startups.failure_reason = failure_idea_patterns.idea_category
               GROUP BY failure_idea_patterns.idea_category
               LIMIT 10"""
        )
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                lines.append(f"### {r['idea_category']}")
                if r.get("examples"):
                    lines.append(f"Examples: {r['examples'][:200]}")
                lines.append("")
        return lines

    def _section_survival_rates(self, cursor) -> list[str]:
        lines = ["## Survival Rate Analysis", ""]
        cursor.execute(
            """SELECT industry_name, year, age_1_yr_survival, age_5_yr_survival
               FROM bls_survival_rates ORDER BY year DESC LIMIT 10"""
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
        return lines

    def _section_growth_factors(self, cursor) -> list[str]:
        lines = ["## Growth Factors", ""]
        lines.append("Based on analysis of successful startups:")
        lines.append("- **Team resilience** — Ability to pivot from failure")
        lines.append("- **Market timing** — Launching in favorable policy windows")
        lines.append("- **Capital efficiency** — Sustainable growth without over-raising")
        lines.append("")
        return lines

    # Generic section
    def _section_generic_header(self, topic: str, now: datetime) -> list[str]:
        return [
            f"# {topic or 'Research Report'}",
            "",
            f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "---",
            "",
        ]

    def _section_data_summary(self, cursor) -> list[str]:
        """Data summary section."""
        lines = ["## Data Summary", ""]
        cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
        count = cursor.fetchone()
        lines.append(f"- **Total failed startups:** {count['cnt'] if count else 0:,}")
        lines.append("")
        return lines

    # ══════════════════════════════════════════════════════════════════════════
    # Task 4: AI Research (Ask) Methods
    # ══════════════════════════════════════════════════════════════════════════

    def research(self, query: str) -> AgentResult:
        """Deep research query over the data using natural language."""
        _logger.info("SpanAgent: Research query: %s", query[:80])

        # Use AIAnalystAgent internally for query processing
        from agents.ai_analyst_agent import AIAnalystAgent

        analyst_config = self.config.copy()
        analyst_config["_pipeline_name"] = "span-research"
        analyst_config["_scheduled"] = False

        analyst = AIAnalystAgent(config=analyst_config, dry_run=self.dry_run, query=query)
        result = analyst.run()

        # Track the research query
        self._log_research_query(query, result)

        return result

    def compare_sectors(self, sectors: list[str]) -> AgentResult:
        """Compare multiple sectors side-by-side."""
        if not sectors or len(sectors) < 2:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=["Please provide at least 2 sectors to compare"],
            )

        # Build comparison query
        query = f"What are the key differences between these sectors: {', '.join(sectors)}?"
        return self.research(query)

    def find_opportunities(self, criteria: dict | None = None) -> AgentResult:
        """Find opportunities matching criteria."""
        criteria = criteria or {}
        sector = criteria.get("sector", "")
        region = criteria.get("region", "")
        min_score = criteria.get("min_opportunity_score", 60)

        query = "Find manufacturing revival opportunities"
        if sector:
            query += f" in the {sector} sector"
        if region:
            query += f" in {region}"
        query += f" with opportunity scores above {min_score}"

        return self.research(query)

    def _log_research_query(self, query: str, result: AgentResult) -> None:
        """Log research query for span tracking."""
        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO span_snapshots
                   (pipeline_name, agent_name, duration_seconds, records_affected,
                    status, anomaly_detected, anomaly_type, anomaly_detail, snapshot_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    "span-research",
                    "ai_analyst",
                    0,  # Duration tracked by analyst
                    result.data.get("rows_returned", 0),
                    result.status,
                    1 if result.errors else 0,
                    "query_error" if result.errors else None,
                    query[:200] if result.errors else None,
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            _logger.error("SpanAgent: Failed to log research query: %s", e)

    # ══════════════════════════════════════════════════════════════════════════
    # Unified Entry Point (for CLI --span flag)
    # ══════════════════════════════════════════════════════════════════════════

    def run_unified(self, action: str, **kwargs) -> AgentResult:
        """Unified entry point for all span operations.

        Actions:
        - run: Execute pipeline
        - status: Get pipeline status
        - ask: Research query
        - report: Generate report
        """
        if action == "run":
            pipeline = kwargs.get("pipeline", "daily")
            return self.run_pipeline(pipeline)

        elif action == "status":
            status = self.get_pipeline_status()
            print(json.dumps(status, indent=2, default=str))
            return AgentResult(
                agent_name=self.name,
                status="success",
                data=status,
            )

        elif action == "ask":
            query = kwargs.get("query", "")
            return self.research(query)

        elif action == "report":
            template = kwargs.get("type", "opportunity_report")
            topic = kwargs.get("topic", "")
            return self.generate_research_report(template, topic)

        elif action == "compare":
            sectors = kwargs.get("sectors", [])
            return self.compare_sectors(sectors)

        elif action == "opportunities":
            criteria = kwargs.get("criteria", {})
            return self.find_opportunities(criteria)

        else:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[f"Unknown action: {action}"],
            )
