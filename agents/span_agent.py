"""Span Agent — pipeline health monitor with anomaly detection.

Monitors agent pipeline runs for performance regressions, failure patterns,
and data quality drops. Stores health snapshots in span_snapshots table.

Anomaly detection (threshold-based):
- slow_run: agent duration > 2x rolling average
- high_failure: failure rate > 10% in lookback window
- data_drop: records_affected dropped > 50% vs previous run

Runs after every pipeline execution (daily, weekly, full).
Prints a health report with actionable suggestions to stdout.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


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

        _logger.info("SpanAgent: Analyzing pipeline '%s' health (lookback=%dd)", pipeline_name, lookback_days)

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
            cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d %H:%M:%S")
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
                    dur = self._parse_duration(run.get("started_at"), run.get("completed_at"))
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
                    anomaly_detail = anomaly_detail or f"Failure rate {failure_pct:.1f}% ({failure_count}/{len(statuses)})"
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
                        anomaly_detail = anomaly_detail or f"Records dropped {drop_pct:.0f}% ({prev_records} -> {last_records})"
                        suggestions.append(
                            f"  [DROP] {agent_name}: {anomaly_detail}. "
                            f"Verify data source hasn't changed format or rate-limited."
                        )

                # Health score
                health_score = self._compute_health(avg_duration, last_duration, failure_pct, last_records)

                # Health report entry
                health_report.append({
                    "agent": agent_name,
                    "runs": len(agent_history),
                    "avg_duration": avg_duration,
                    "last_duration": last_duration,
                    "failure_pct": failure_pct,
                    "avg_records": avg_records,
                    "health": health_score,
                    "anomaly": anomaly_type,
                })

                # Insert snapshot
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """INSERT INTO span_snapshots
                       (pipeline_name, agent_name, duration_seconds, records_affected,
                        status, anomaly_detected, anomaly_type, anomaly_detail, snapshot_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        pipeline_name, agent_name, last_duration, last_records,
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
                len(health_report), anomalies_found, snapshots_inserted,
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
                errors=[f"{anomalies_found} anomalies detected"] if anomalies_found else [],
            )

        except Exception as e:
            _logger.error("SpanAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

    def _parse_duration(self, started_at: str | None, completed_at: str | None) -> float | None:
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

    def _compute_health(self, avg_dur: float, last_dur: float,
                       failure_pct: float, records: int) -> str:
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
        print(f"  {'Agent':<25} {'Runs':>4} {'Avg(s)':>7} {'Last(s)':>7} {'Fail%':>6} {'Health':>7}")
        print(f"  {'-'*25} {'-'*4} {'-'*7} {'-'*7} {'-'*6} {'-'*7}")

        for entry in report:
            health_icon = {"green": "OK", "yellow": "WARN", "red": "FAIL"}.get(entry["health"], "?")
            anomaly_flag = " !" if entry["anomaly"] else ""
            print(
                f"  {entry['agent']:<25} {entry['runs']:>4} "
                f"{entry['avg_duration']:>7.1f} {entry['last_duration']:>7.1f} "
                f"{entry['failure_pct']:>5.1f}% {health_icon:>7}{anomaly_flag}"
            )

        if suggestions:
            print(f"\n  SUGGESTIONS:")
            for s in suggestions:
                print(s)

        print(f"\n{'='*60}\n")
