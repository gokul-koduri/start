"""Failure Pattern Analysis Agent — deep analysis of startup failure patterns."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class FailurePatternAgent(BaseAgent):
    """Analyzes failure patterns across sectors, funding levels, and time.

    Produces:
    - Sector failure clustering
    - Funding bracket analysis ($0-10M, $10-50M, $50-100M, $100M+)
    - Year-over-year failure trends
    - Top failure reasons by manufacturing sub-sector
    - Regional failure density
    """

    @property
    def name(self) -> str:
        return "failure_pattern"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # 1. Sector failure clustering
        cursor = conn.cursor()
        cursor.execute(
            """SELECT sector, COUNT(*) as count,
                      AVG(funding_raised_usd) as avg_funding,
                      SUM(CASE WHEN manufacturing_sub_sector IS NOT NULL THEN 1 ELSE 0 END) as mfg_count
               FROM failed_startups
               GROUP BY sector
               ORDER BY count DESC
               LIMIT 15"""
        )
        sector_clusters = cursor.fetchall()
        insights["sector_clusters"] = [dict(r) for r in sector_clusters]
        cursor.close()

        # 2. Funding bracket analysis
        cursor = conn.cursor()
        cursor.execute(
            """SELECT
                 CASE
                   WHEN funding_raised_usd < 10000000 THEN '$0-10M'
                   WHEN funding_raised_usd < 50000000 THEN '$10-50M'
                   WHEN funding_raised_usd < 100000000 THEN '$50-100M'
                   ELSE '$100M+'
                 END as bracket,
                 COUNT(*) as count,
                 AVG(funding_raised_usd) as avg_funding,
                 MIN(year_shutdown) as earliest,
                 MAX(year_shutdown) as latest
               FROM failed_startups
               WHERE funding_raised_usd IS NOT NULL
               GROUP BY bracket
               ORDER BY avg_funding"""
        )
        funding_brackets = cursor.fetchall()
        insights["funding_brackets"] = [dict(r) for r in funding_brackets]
        cursor.close()

        # 3. Year-over-year failure trends
        cursor = conn.cursor()
        cursor.execute(
            """SELECT year_shutdown, COUNT(*) as failures,
                      AVG(funding_raised_usd) as avg_funding,
                      SUM(CASE WHEN manufacturing_sub_sector IS NOT NULL THEN 1 ELSE 0 END) as mfg_failures
               FROM failed_startups
               WHERE year_shutdown >= 2018
               GROUP BY year_shutdown
               ORDER BY year_shutdown"""
        )
        yearly_trends = cursor.fetchall()
        insights["yearly_trends"] = [dict(r) for r in yearly_trends]
        cursor.close()

        # 4. Top failure reasons for manufacturing startups
        cursor = conn.cursor()
        cursor.execute(
            """SELECT failure_category, COUNT(*) as count,
                      GROUP_CONCAT(DISTINCT manufacturing_sub_sector SEPARATOR ',') as sub_sectors
               FROM failed_startups
               WHERE manufacturing_sub_sector IS NOT NULL
               GROUP BY failure_category
               ORDER BY count DESC
               LIMIT 10"""
        )
        mfg_failure_reasons = cursor.fetchall()
        insights["mfg_failure_reasons"] = [dict(r) for r in mfg_failure_reasons]
        cursor.close()

        # 5. Manufacturing sub-sector breakdown
        cursor = conn.cursor()
        cursor.execute(
            """SELECT manufacturing_sub_sector, COUNT(*) as count,
                      AVG(funding_raised_usd) as avg_funding,
                      AVG(year_shutdown - year_founded) as avg_lifespan_years
               FROM failed_startups
               WHERE manufacturing_sub_sector IS NOT NULL
               GROUP BY manufacturing_sub_sector
               ORDER BY count DESC"""
        )
        sub_sector_breakdown = cursor.fetchall()
        insights["sub_sector_breakdown"] = [dict(r) for r in sub_sector_breakdown]
        cursor.close()

        # 6. Top 10 highest-funded failures
        cursor = conn.cursor()
        cursor.execute(
            """SELECT name, sector, funding_raised_usd, year_shutdown, failure_reason
               FROM failed_startups
               ORDER BY funding_raised_usd DESC
               LIMIT 10"""
        )
        top_funded = cursor.fetchall()
        insights["top_funded_failures"] = [dict(r) for r in top_funded]
        cursor.close()

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_failure_patterns")
        cursor.execute(
            """INSERT INTO analysis_failure_patterns
               (analysis_type, insights_json, analyzed_at, record_count)
               VALUES (%s, %s, %s, %s)""",
            (
                "failure_pattern_full",
                json.dumps(insights, default=str),
                datetime.now(timezone.utc).isoformat(),
                sum(s["count"] for s in sector_clusters),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        _logger.info(
            "FailurePatternAgent: Analyzed %d sectors, %d funding brackets, %d years",
            len(sector_clusters),
            len(funding_brackets),
            len(yearly_trends),
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "sector_clusters": len(sector_clusters),
                "funding_brackets": len(funding_brackets),
                "yearly_trends": len(yearly_trends),
                "records_affected": len(sector_clusters) + len(funding_brackets),
                "top_insight": f"Top sector: {sector_clusters[0]['sector']} ({sector_clusters[0]['count']} failures)"
                if sector_clusters
                else "No data",
            },
        )
