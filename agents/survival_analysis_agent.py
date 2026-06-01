"""Survival Analysis Agent — BLS survival rate trend analysis and projections."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class SurvivalAnalysisAgent(BaseAgent):
    """Analyzes manufacturing survival rates from BLS data.

    Produces:
    - Survival rate trends over time
    - Year-over-year changes in 1yr/5yr survival
    - Failure probability projections
    - Comparison of survival rates across years
    """

    @property
    def name(self) -> str:
        return "survival_analysis"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # 1. Overall survival rate trends
        cursor = conn.cursor()
        cursor.execute(
            """SELECT year, industry_name,
                      age_1_yr_survival, age_2_yr_survival,
                      age_3_yr_survival, age_5_yr_survival,
                      establishment_count
               FROM bls_survival_rates
               WHERE quarter IS NULL
               ORDER BY year"""
        )
        survival_trends = cursor.fetchall()
        insights["survival_trends"] = [dict(r) for r in survival_trends]
        cursor.close()

        # 2. Year-over-year changes
        yoy_changes = []
        rows = [dict(r) for r in survival_trends]
        for i in range(1, len(rows)):
            prev, curr = rows[i - 1], rows[i]
            change = {}
            change["year"] = curr["year"]
            change["prev_year"] = prev["year"]
            if prev["age_1_yr_survival"] and curr["age_1_yr_survival"]:
                change["change_1yr"] = round(curr["age_1_yr_survival"] - prev["age_1_yr_survival"], 2)
            if prev["age_5_yr_survival"] and curr["age_5_yr_survival"]:
                change["change_5yr"] = round(curr["age_5_yr_survival"] - prev["age_5_yr_survival"], 2)
            yoy_changes.append(change)
        insights["year_over_year_changes"] = yoy_changes

        # 3. Failure probability analysis
        failure_probs = []
        for row in rows:
            if row["age_1_yr_survival"]:
                fp = {
                    "year": row["year"],
                    "failure_rate_1yr": round(100 - row["age_1_yr_survival"], 1),
                    "failure_rate_5yr": round(100 - row["age_5_yr_survival"], 1) if row["age_5_yr_survival"] else None,
                    "establishments_at_risk": row["establishment_count"],
                }
                failure_probs.append(fp)
        insights["failure_probabilities"] = failure_probs

        # 4. Average survival rates
        cursor = conn.cursor()
        cursor.execute(
            """SELECT AVG(age_1_yr_survival) as avg_1yr,
                      AVG(age_2_yr_survival) as avg_2yr,
                      AVG(age_3_yr_survival) as avg_3yr,
                      AVG(age_5_yr_survival) as avg_5yr,
                      COUNT(*) as data_points
               FROM bls_survival_rates
               WHERE quarter IS NULL"""
        )
        avg_survival = cursor.fetchone()
        cursor.close()
        if avg_survival:
            insights["average_survival"] = dict(avg_survival)

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_survival_trends")
        cursor.execute(
            """INSERT INTO analysis_survival_trends
               (analysis_type, insights_json, analyzed_at, record_count)
               VALUES (%s, %s, %s, %s)""",
            (
                "survival_trends_full",
                json.dumps(insights, default=str),
                datetime.now(timezone.utc).isoformat(),
                len(survival_trends),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        avg_5yr = insights.get("average_survival", {}).get("avg_5yr", 0)
        _logger.info("SurvivalAnalysisAgent: %d data points, avg 5yr survival: %.1f%%",
                     len(survival_trends), avg_5yr or 0)

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "data_points": len(survival_trends),
                "avg_5yr_survival": round(avg_5yr, 1) if avg_5yr else None,
                "avg_1yr_failure_rate": round(100 - (insights.get("average_survival", {}).get("avg_1yr", 0)), 1),
                "records_affected": len(survival_trends),
                "top_insight": f"Avg 5yr manufacturing survival: {round(avg_5yr, 1)}% (failure rate: {round(100 - avg_5yr, 1)}%)"
                    if avg_5yr else "Insufficient BLS data",
            },
        )
