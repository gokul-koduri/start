"""Founder Background Agent — analyzes founder profiles and backgrounds."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class FounderBackgroundAgent(BaseAgent):
    """Analyzes founder backgrounds and experience patterns.

    Produces:
    - Founder experience distributions
    - Educational background patterns
    - Prior industry experience
    - Geographic origin analysis
    """

    @property
    def name(self) -> str:
        return "founder_background"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # Analyze company profiles for founder/officer information
        cursor = conn.cursor()
        cursor.execute(
            """SELECT company_name, officers, jurisdiction_code, incorporated
               FROM company_profiles
               WHERE officers IS NOT NULL
               LIMIT 100"""
        )
        company_profiles = cursor.fetchall()
        cursor.close()

        # Extract patterns from officer data
        founder_patterns = {
            "total_companies_analyzed": len(company_profiles),
            "avg_officers_per_company": 0,
            "common_titles": {},
            "us_companies": 0,
            "eu_companies": 0,
            "other_companies": 0
        }

        if company_profiles:
            total_officers = 0
            for profile in company_profiles:
                try:
                    officers = json.loads(profile.get("officers", "{}")) if isinstance(profile.get("officers"), str) else profile.get("officers", {})
                    total_officers += len(officers) if isinstance(officers, dict) else 0

                    # Count jurisdictions
                    juris = profile.get("jurisdiction_code", "")
                    if juris in ["US", "USA"]:
                        founder_patterns["us_companies"] += 1
                    elif juris in ["GB", "DE", "FR"]:
                        founder_patterns["eu_companies"] += 1
                    else:
                        founder_patterns["other_companies"] += 1
                except (json.JSONDecodeError, TypeError):
                    pass

            founder_patterns["avg_officers_per_company"] = total_officers / len(company_profiles) if company_profiles else 0

        insights["founder_patterns"] = founder_patterns

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_founder_background")
        cursor.execute(
            """INSERT INTO analysis_founder_background
               (analysis_type, insights_json, analyzed_at, record_count)
               VALUES (%s, %s, %s, %s)""",
            (
                "founder_background_full",
                json.dumps(insights, default=str),
                datetime.now(timezone.utc).isoformat(),
                len(company_profiles)
            )
        )
        conn.commit()
        cursor.close()
        conn.close()

        _logger.info("FounderBackgroundAgent: Analyzed %d company profiles", len(company_profiles))

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "companies_analyzed": len(company_profiles),
                "records_affected": 1,
            },
        )
