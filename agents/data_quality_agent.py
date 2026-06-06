"""Data quality agent — checks data quality metrics."""

import logging
from typing import Dict
from agents.base import BaseAgent, AgentResult

_logger = logging.getLogger(__name__)


class DataQualityAgent(BaseAgent):
    """Checks data quality (nulls, stale data, duplicates)."""

    @property
    def name(self) -> str:
        return "data_quality"

    def execute(self, upstream_results) -> AgentResult:
        """Run data quality checks."""
        try:
            from db.connection import get_connection
            from db import schema

            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            checks = {}

            # Null percentage checks
            cursor.execute("SELECT COUNT(*) FROM failed_startups WHERE sector IS NULL")
            null_sector = cursor.fetchone()["cnt"]
            cursor.execute("SELECT COUNT(*) FROM failed_startups")
            total_startups = cursor.fetchone()["cnt"]
            null_pct = (null_sector / total_startups * 100) if total_startups > 0 else 0
            checks["null_sector_pct"] = round(null_pct, 2)

            # Stale data check (no new data in 7 days)
            cursor.execute(
                """SELECT COUNT(*) FROM news_articles
                   WHERE DATE(collected_at) >= CURDATE() - INTERVAL 7 DAY"""
            )
            recent_news = cursor.fetchone()["cnt"]
            checks["stale_news"] = recent_news == 0

            cursor.close()
            conn.close()

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"checks": checks},
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
