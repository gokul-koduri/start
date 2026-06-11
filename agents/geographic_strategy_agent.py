"""Geographic Strategy Agent — regional analysis of failures and revival potential."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class GeographicStrategyAgent(BaseAgent):
    """Analyzes regional failure patterns and revival potential.

    Produces:
    - Regional failure density map
    - Manufacturing failure concentration by area
    - Revival potential scoring per region
    - Recommended focus areas
    """

    @property
    def name(self) -> str:
        return "geographic_strategy"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # 1. Regional failure distribution
        cursor = conn.cursor()
        cursor.execute(
            """SELECT
                 COALESCE(region, country, 'Unknown') as area,
                 COUNT(*) as total_failures,
                 SUM(CASE WHEN manufacturing_sub_sector IS NOT NULL THEN 1 ELSE 0 END) as mfg_failures,
                 AVG(funding_raised_usd) as avg_funding,
                 GROUP_CONCAT(DISTINCT sector SEPARATOR ',') as sectors
               FROM failed_startups
               GROUP BY area
               ORDER BY total_failures DESC"""
        )
        regional_failures = cursor.fetchall()
        insights["regional_failures"] = [dict(r) for r in regional_failures]
        cursor.close()

        # 2. Country-level breakdown
        cursor = conn.cursor()
        cursor.execute(
            """SELECT country,
                      COUNT(*) as failures,
                      SUM(CASE WHEN manufacturing_sub_sector IS NOT NULL THEN 1 ELSE 0 END) as mfg_failures,
                      AVG(funding_raised_usd) as avg_funding,
                      AVG(year_shutdown - year_founded) as avg_lifespan
               FROM failed_startups
               WHERE country IS NOT NULL
               GROUP BY country
               ORDER BY failures DESC
               LIMIT 15"""
        )
        country_breakdown = cursor.fetchall()
        insights["country_breakdown"] = [dict(r) for r in country_breakdown]
        cursor.close()

        # 3. Geographic hotspots from curated data
        cursor = conn.cursor()
        cursor.execute(
            """SELECT region, closed_facility_types, revival_potential
               FROM geographic_hotspots"""
        )
        hotspots = cursor.fetchall()
        insights["hotspots"] = [dict(r) for r in hotspots]
        cursor.close()

        # 4. Regional revival scoring
        regional_scores = []
        for rf in regional_failures:
            area = dict(rf)
            score = 0
            # Higher failures = more data = more opportunities to learn
            if area["total_failures"] >= 20:
                score += 30
            elif area["total_failures"] >= 10:
                score += 20
            elif area["total_failures"] >= 5:
                score += 10
            # Manufacturing concentration
            if area["mfg_failures"] and area["total_failures"]:
                mfg_ratio = area["mfg_failures"] / area["total_failures"]
                score += int(mfg_ratio * 30)
            # High funding = more capital available
            if area["avg_funding"] and area["avg_funding"] > 100_000_000:
                score += 20
            elif area["avg_funding"] and area["avg_funding"] > 50_000_000:
                score += 10
            # Check if it's a known hotspot
            for h in hotspots:
                if h["region"].lower() in area["area"].lower():
                    score += 20
                    break
            area["revival_score"] = min(score, 100)
            regional_scores.append(area)

        regional_scores.sort(key=lambda x: x["revival_score"], reverse=True)
        insights["regional_scores"] = regional_scores

        # 5. Manufacturing sub-sector by region
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COALESCE(region, country, 'Unknown') as area,
                      manufacturing_sub_sector,
                      COUNT(*) as count,
                      AVG(funding_raised_usd) as avg_funding
               FROM failed_startups
               WHERE manufacturing_sub_sector IS NOT NULL
               GROUP BY area, manufacturing_sub_sector
               ORDER BY count DESC
               LIMIT 20"""
        )
        mfg_by_region = cursor.fetchall()
        insights["mfg_by_region"] = [dict(r) for r in mfg_by_region]
        cursor.close()

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_geographic_strategy")
        cursor.execute(
            """INSERT INTO analysis_geographic_strategy
               (analysis_type, insights_json, analyzed_at, record_count)
               VALUES (%s, %s, %s, %s)""",
            (
                "geographic_strategy_full",
                json.dumps(insights, default=str),
                datetime.now(timezone.utc).isoformat(),
                len(regional_failures),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        top_region = regional_scores[0]["area"] if regional_scores else "N/A"
        _logger.info(
            "GeographicStrategyAgent: %d regions analyzed, top: %s",
            len(regional_scores),
            top_region,
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "regions_analyzed": len(regional_scores),
                "countries_analyzed": len(country_breakdown),
                "top_region": top_region,
                "records_affected": len(regional_failures),
                "top_insight": f"Top region: {top_region} ({regional_scores[0]['total_failures']} failures)"
                if regional_scores
                else "No regional data",
            },
        )
