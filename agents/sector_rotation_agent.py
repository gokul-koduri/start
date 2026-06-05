"""Analysis agent."""


import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class SectorRotationAgent(BaseAgent):
    """Analysis agent."""

    @property
    def name(self) -> str:
        return "sector_rotation"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        # Query database
        cursor = conn.cursor()
        cursor.execute(
            """SELECT sector, COUNT(*) as count
               FROM failed_startups
               WHERE sector IS NOT NULL
               GROUP BY sector
               LIMIT 10"""
        )
        results = cursor.fetchall()
        cursor.close()

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_sector_rotation")
        cursor.execute(
            """INSERT INTO analysis_sector_rotation (analyzed_at, record_count)
               VALUES (%s, %s)""",
            (datetime.now(timezone.utc).isoformat(), len(results))
        )
        conn.commit()
        cursor.close()
        conn.close()

        _logger.info("SectorRotationAgent: Analyzed %d records", len(results))

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={"records_affected": len(results)},
        )
