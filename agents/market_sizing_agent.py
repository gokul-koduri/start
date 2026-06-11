"""Market Sizing Agent — estimates market sizes for startup sectors."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class MarketSizingAgent(BaseAgent):
    """Analyzes and estimates market sizes for startup sectors.

    Produces:
    - Sector-level market size estimates
    - Growth rate projections
    - Confidence scores based on data availability
    - Data source attribution
    """

    @property
    def name(self) -> str:
        return "market_sizing"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # 1. Analyze failed startups by sector for market signals
        cursor = conn.cursor()
        cursor.execute(
            """SELECT sector, COUNT(*) as failure_count,
                      AVG(funding_raised_usd) as avg_funding,
                      SUM(funding_raised_usd) as total_funding
               FROM failed_startups
               WHERE funding_raised_usd IS NOT NULL
               GROUP BY sector
               ORDER BY failure_count DESC
               LIMIT 20"""
        )
        sector_failures = cursor.fetchall()
        insights["sector_failures"] = [dict(r) for r in sector_failures]
        cursor.close()

        # 2. Analyze funding events by sector
        cursor = conn.cursor()
        cursor.execute(
            """SELECT fe.company_name, fe.round_type, fe.amount_usd,
                      fs.sector
               FROM funding_events fe
               LEFT JOIN failed_startups fs ON fe.company_name = fs.name
               WHERE fe.amount_usd IS NOT NULL
               ORDER BY fe.amount_usd DESC
               LIMIT 100"""
        )
        funding_by_sector = cursor.fetchall()
        insights["funding_by_sector"] = [dict(r) for r in funding_by_sector]
        cursor.close()

        # 3. Estimate market sizes based on sector activity
        market_estimates = []
        for sector_row in sector_failures:
            sector = sector_row["sector"]
            if not sector:
                continue

            # Simple market size estimation heuristic
            # Total funding in sector * multiplier (conservative 3x)
            total_funding = sector_row.get("total_funding", 0) or 0
            failure_count = sector_row.get("failure_count", 0) or 0

            # Estimate market size as 3-10x of total funding seen
            # Higher multiplier for sectors with more failures (indicating larger market)
            if failure_count > 50:
                multiplier = 10
            elif failure_count > 20:
                multiplier = 5
            else:
                multiplier = 3

            estimated_market_size = total_funding * multiplier

            # Confidence score based on data volume
            if failure_count >= 30:
                confidence = 0.8
            elif failure_count >= 10:
                confidence = 0.6
            else:
                confidence = 0.4

            # Growth rate (simplified projection based on recent activity)
            # Default to 15% for emerging markets, 5% for mature
            if sector in ["AI", "Crypto/Blockchain", "ClimateTech", "EdTech"]:
                growth_rate = 0.20
            elif sector in ["SaaS", "Fintech", "E-commerce"]:
                growth_rate = 0.15
            else:
                growth_rate = 0.08

            market_estimates.append(
                {
                    "sector": sector,
                    "market_size_usd": estimated_market_size,
                    "growth_rate": growth_rate,
                    "confidence_score": confidence,
                    "data_sources": {
                        "failed_startups_count": failure_count,
                        "total_funding_analyzed": total_funding,
                        "multiplier_used": multiplier,
                    },
                    "methodology": "funding_multiplier",
                }
            )

        insights["market_estimates"] = market_estimates

        # Store results in database
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_market_sizing")

        for estimate in market_estimates:
            cursor.execute(
                """INSERT INTO analysis_market_sizing
                   (sector, market_size_usd, growth_rate, confidence_score,
                    data_sources, methodology, analyzed_at, record_count)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    estimate["sector"],
                    estimate["market_size_usd"],
                    estimate["growth_rate"],
                    estimate["confidence_score"],
                    json.dumps(estimate["data_sources"]),
                    estimate["methodology"],
                    datetime.now(timezone.utc).isoformat(),
                    estimate["data_sources"].get("failed_startups_count", 0),
                ),
            )

        conn.commit()
        cursor.close()
        conn.close()

        _logger.info(
            "MarketSizingAgent: Analyzed %d sectors, estimated %d market sizes",
            len(sector_failures),
            len(market_estimates),
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "sectors_analyzed": len(sector_failures),
                "market_estimates": len(market_estimates),
                "records_affected": len(market_estimates),
                "top_insight": f"Largest market: {market_estimates[0]['sector']} (${market_estimates[0]['market_size_usd']:,.0f})"
                if market_estimates
                else "No data",
            },
        )
