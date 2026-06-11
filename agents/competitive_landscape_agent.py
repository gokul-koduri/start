"""Competitive Landscape Agent — analyzes competitive dynamics across sectors."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class CompetitiveLandscapeAgent(BaseAgent):
    """Analyzes competitive landscape and market dynamics.

    Produces:
    - Competitor counts by sector
    - Market concentration metrics
    - Fragmentation scores
    - Entry barriers assessment
    - Rivalry intensity indicators
    """

    @property
    def name(self) -> str:
        return "competitive_landscape"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # 1. Count competitors by sector
        cursor = conn.cursor()
        cursor.execute(
            """SELECT sector, COUNT(*) as competitor_count,
                      AVG(funding_raised_usd) as avg_funding,
                      COUNT(CASE WHEN funding_raised_usd > 50000000 THEN 1 END) as well_funded_count
               FROM failed_startups
               WHERE sector IS NOT NULL
               GROUP BY sector
               ORDER BY competitor_count DESC
               LIMIT 20"""
        )
        sector_competitors = cursor.fetchall()
        cursor.close()

        # 2. Analyze market dynamics for each sector
        landscape_data = []
        for sector_row in sector_competitors:
            sector = sector_row["sector"]
            if not sector:
                continue

            competitor_count = sector_row.get("competitor_count", 0) or 0
            avg_funding = sector_row.get("avg_funding", 0) or 0
            sector_row.get("well_funded_count", 0) or 0

            # Market concentration (inverse of competitor count normalized)
            # Fewer competitors = higher concentration
            if competitor_count > 50:
                market_concentration = 0.2  # Fragmented
                fragmentation_score = 0.8
            elif competitor_count > 20:
                market_concentration = 0.4  # Moderately fragmented
                fragmentation_score = 0.6
            elif competitor_count > 10:
                market_concentration = 0.6  # Moderately concentrated
                fragmentation_score = 0.4
            else:
                market_concentration = 0.8  # Concentrated
                fragmentation_score = 0.2

            # Entry barriers based on sector characteristics
            if sector in ["Semiconductors", "Biotech", "CleanTech", "Manufacturing"]:
                entry_barriers = "high"
            elif sector in ["SaaS", "Fintech", "E-commerce"]:
                entry_barriers = "medium"
            else:
                entry_barriers = "low"

            # Rivalry intensity based on competitor count and funding
            if competitor_count > 40 and avg_funding > 10_000_000:
                rivalry_intensity = "high"
            elif competitor_count > 20:
                rivalry_intensity = "medium"
            else:
                rivalry_intensity = "low"

            # Get top competitors (by funding)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT name, funding_raised_usd, year_founded, failure_reason
                   FROM failed_startups
                   WHERE sector = %s AND funding_raised_usd IS NOT NULL
                   ORDER BY funding_raised_usd DESC
                   LIMIT 5""",
                (sector,),
            )
            top_competitors = cursor.fetchall()
            cursor.close()

            landscape_data.append(
                {
                    "sector": sector,
                    "competitor_count": competitor_count,
                    "market_concentration": market_concentration,
                    "fragmentation_score": fragmentation_score,
                    "avg_funding_competitors": avg_funding,
                    "top_competitors_json": json.dumps(
                        [dict(c) for c in top_competitors], default=str
                    ),
                    "entry_barriers": entry_barriers,
                    "rivalry_intensity": rivalry_intensity,
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "record_count": competitor_count,
                }
            )

        insights["landscape_data"] = landscape_data

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_competitive_landscape")

        for data in landscape_data:
            cursor.execute(
                """INSERT INTO analysis_competitive_landscape
                   (sector, competitor_count, market_concentration, fragmentation_score,
                    avg_funding_competitors, top_competitors_json, entry_barriers,
                    rivalry_intensity, analyzed_at, record_count)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    data["sector"],
                    data["competitor_count"],
                    data["market_concentration"],
                    data["fragmentation_score"],
                    data["avg_funding_competitors"],
                    data["top_competitors_json"],
                    data["entry_barriers"],
                    data["rivalry_intensity"],
                    data["analyzed_at"],
                    data["record_count"],
                ),
            )

        conn.commit()
        cursor.close()
        conn.close()

        _logger.info(
            "CompetitiveLandscapeAgent: Analyzed %d sectors", len(landscape_data)
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "sectors_analyzed": len(landscape_data),
                "records_affected": len(landscape_data),
                "top_insight": f"Most competitive: {landscape_data[0]['sector']} ({landscape_data[0]['competitor_count']} competitors)"
                if landscape_data
                else "No data",
            },
        )
