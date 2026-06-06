"""Pipeline health agent — monitors pipeline execution."""

import logging
from typing import Dict
from agents.base import BaseAgent, AgentResult
from datetime import datetime, timezone, timedelta

_logger = logging.getLogger(__name__)


class PipelineHealthAgent(BaseAgent):
    """Monitors pipeline execution health."""

    @property
    def name(self) -> str:
        return "pipeline_health"

    def execute(self, upstream_results) -> AgentResult:
        """Check pipeline health."""
        try:
            from db.connection import get_connection
            from db import schema

            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            # Check recent pipeline runs
            cursor.execute(
                """SELECT status, COUNT(*) as cnt
                   FROM agent_runs
                   WHERE started_at >= %s
                   GROUP BY status""",
                ((datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(),)
            )
            status_counts = {dict(r)["status"]: dict(r)["cnt"] for r in cursor.fetchall()}

            total_runs = sum(status_counts.values())
            success_rate = (status_counts.get("success", 0) / total_runs * 100) if total_runs > 0 else 0

            cursor.close()
            conn.close()

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "last_24h_runs": total_runs,
                    "success_rate": round(success_rate, 2),
                    "status_counts": status_counts,
                },
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
