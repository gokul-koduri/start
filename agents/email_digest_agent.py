"""Email digest agent — generates email digests."""

import logging
from typing import Dict
from agents.base import BaseAgent, AgentResult
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)


class EmailDigestAgent(BaseAgent):
    """Generates and sends email digests."""

    @property
    def name(self) -> str:
        return "email_digest"

    def execute(self, upstream_results) -> AgentResult:
        """Generate email digest."""
        try:
            from db.connection import get_connection
            from db import schema

            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            # Get recent stats
            cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
            startup_count = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM news_articles WHERE DATE(collected_at) = CURDATE()")
            news_today = cursor.fetchone()["cnt"]

            cursor.execute(
                """SELECT COUNT(*) as cnt FROM opportunity_scores WHERE composite_score >= 70"""
            )
            high_value_opportunities = cursor.fetchone()["cnt"]

            cursor.close()
            conn.close()

            digest = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "stats": {
                    "total_startups": startup_count,
                    "news_today": news_today,
                    "high_value_opportunities": high_value_opportunities,
                }
            }

            return AgentResult(
                agent_name=self.name,
                status="success",
                data=digest,
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
