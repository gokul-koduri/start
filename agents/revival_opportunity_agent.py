"""Revival Opportunity Agent — manufacturing revival and reshoring analysis."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class RevivalOpportunityAgent(BaseAgent):
    """Analyzes manufacturing revival opportunities from reshoring and failure data.

    Produces:
    - Top revival industries with scoring
    - Reshoring job creation trends
    - Failed manufacturing startups that could be revived
    - ROI potential assessment per industry
    """

    @property
    def name(self) -> str:
        return "revival_opportunity"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # 1. Revival industries analysis
        cursor = conn.cursor()
        cursor.execute(
            """SELECT industry, died_period, why_returning,
                      closed_site_types, market_fit, key_investors, market_size_2030
               FROM revival_industries"""
        )
        revival_industries = cursor.fetchall()
        insights["revival_industries"] = [dict(r) for r in revival_industries]
        cursor.close()

        # 2. Reshoring trends
        cursor = conn.cursor()
        cursor.execute(
            """SELECT data_year,
                      SUM(jobs_created) as total_jobs,
                      SUM(project_count) as total_projects,
                      AVG(success_rate_pct) as avg_success_rate
               FROM reshoring_data
               GROUP BY data_year
               ORDER BY data_year"""
        )
        reshoring_trends = cursor.fetchall()
        insights["reshoring_trends"] = [dict(r) for r in reshoring_trends]
        cursor.close()

        # 3. Reshoring summary stats
        cursor = conn.cursor()
        cursor.execute(
            """SELECT stat_year, total_jobs, total_reshoring_jobs,
                      total_fdi_jobs, success_rate_pct, headline
               FROM reshoring_summary_stats
               ORDER BY stat_year DESC"""
        )
        summary_stats = cursor.fetchall()
        insights["reshoring_summary"] = [dict(r) for r in summary_stats]
        cursor.close()

        # 4. Failed manufacturing startups eligible for revival
        cursor = conn.cursor()
        cursor.execute(
            """SELECT name, manufacturing_sub_sector, funding_raised_usd,
                      year_shutdown, failure_reason, region,
                      CASE
                        WHEN failure_reason LIKE '%capital%' OR failure_reason LIKE '%funding%' THEN 'capital_issue'
                        WHEN failure_reason LIKE '%scale%' OR failure_reason LIKE '%pilot%' THEN 'scale_issue'
                        WHEN failure_reason LIKE '%supply chain%' THEN 'supply_chain'
                        ELSE 'other'
                      END as revivable_category
               FROM failed_startups
               WHERE manufacturing_sub_sector IS NOT NULL
               ORDER BY funding_raised_usd DESC"""
        )
        revival_candidates = cursor.fetchall()
        insights["revival_candidates"] = [dict(r) for r in revival_candidates]
        cursor.close()

        # 5. Industry revival scoring (cross-reference with reshoring data)
        industry_scores = []
        for ind in revival_industries:
            industry = dict(ind)
            # Count related failed startups
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*) as cnt FROM failed_startups
                   WHERE manufacturing_sub_sector IS NOT NULL
                   AND (failure_reason LIKE %s OR sector LIKE %s)""",
                (f"%{industry['industry']}%", f"%{industry['industry']}%"),
            )
            related = cursor.fetchone()
            cursor.close()
            industry["related_failures"] = related["cnt"] if related else 0

            # Check reshoring activity
            cursor = conn.cursor()
            cursor.execute(
                """SELECT SUM(jobs_created) as jobs, SUM(project_count) as projects
                   FROM reshoring_data WHERE industry LIKE %s""",
                (f"%{industry['industry']}%",),
            )
            reshoring = cursor.fetchone()
            cursor.close()
            industry["reshoring_jobs"] = (
                reshoring["jobs"] if reshoring and reshoring["jobs"] else 0
            )
            industry["reshoring_projects"] = (
                reshoring["projects"] if reshoring and reshoring["projects"] else 0
            )

            # Simple scoring: market fit + reshoring activity + investor interest
            score = 0
            if industry.get("market_fit"):
                score += 30
            if industry.get("key_investors"):
                score += 20
            if industry.get("reshoring_jobs", 0) > 0:
                score += 25
            if industry.get("related_failures", 0) > 0:
                score += 15
            if industry.get("market_size_2030"):
                score += 10
            industry["revival_score"] = min(score, 100)
            industry_scores.append(industry)

        industry_scores.sort(key=lambda x: x["revival_score"], reverse=True)
        insights["industry_revival_scores"] = industry_scores

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_revival_opportunities")
        cursor.execute(
            """INSERT INTO analysis_revival_opportunities
               (analysis_type, insights_json, analyzed_at, record_count)
               VALUES (%s, %s, %s, %s)""",
            (
                "revival_opportunity_full",
                json.dumps(insights, default=str),
                datetime.now(timezone.utc).isoformat(),
                len(revival_candidates),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        top_industry = industry_scores[0]["industry"] if industry_scores else "N/A"
        top_score = industry_scores[0]["revival_score"] if industry_scores else 0
        _logger.info(
            "RevivalOpportunityAgent: %d candidates, top industry: %s (score: %d)",
            len(revival_candidates),
            top_industry,
            top_score,
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "revival_industries": len(revival_industries),
                "revival_candidates": len(revival_candidates),
                "top_industry": top_industry,
                "top_score": top_score,
                "records_affected": len(revival_industries),
                "top_insight": f"Top revival: {top_industry} (score {top_score}/100, {len(revival_candidates)} candidates)",
            },
        )
