"""Pipeline Opportunity Agent - analyzes pipeline data to identify market opportunities.

Includes:
- Market opportunity identification
- Scoring model (0-100)
- Auto-ranking by opportunity score
"""

import json
import logging

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


# Pipeline technology categories that represent opportunities
TECH_GAPS = {
    "smart_pigging": "AI-powered inspection data analysis for inline inspection tools",
    "leak_detection": "Real-time distributed leak detection with fiber optics or drones",
    "corrosion_management": "Predictive corrosion monitoring and management systems",
    "digital_twin": "Pipeline simulation and digital twin solutions",
    "robotic_inspection": "Autonomous inspection robots for difficult-to-access sections",
    "hydrogen_compatible": "Materials and coatings for hydrogen pipeline transport",
    "ai_interpretation": "Machine learning for automated defect detection from inspection data",
    "edge_computing": "On-pipeline edge computing for real-time monitoring",
}

# Scoring components for opportunity evaluation
MARKET_DRIVERS = {
    "smart_pigging": {"demand": 75, "readiness": 80, "regulatory": 60, "investment": 70},
    "leak_detection": {"demand": 85, "readiness": 75, "regulatory": 80, "investment": 65},
    "corrosion_management": {"demand": 70, "readiness": 70, "regulatory": 75, "investment": 55},
    "digital_twin": {"demand": 75, "readiness": 60, "regulatory": 40, "investment": 80},
    "robotic_inspection": {"demand": 65, "readiness": 55, "regulatory": 50, "investment": 60},
    "hydrogen_compatible": {"demand": 80, "readiness": 45, "regulatory": 95, "investment": 70},
    "ai_interpretation": {"demand": 85, "readiness": 70, "regulatory": 30, "investment": 85},
    "edge_computing": {"demand": 60, "readiness": 65, "regulatory": 35, "investment": 55},
}

COMPETITION_LEVELS = {
    "smart_pigging": 70,
    "leak_detection": 65,
    "corrosion_management": 55,
    "digital_twin": 75,
    "robotic_inspection": 45,
    "hydrogen_compatible": 35,
    "ai_interpretation": 60,
    "edge_computing": 50,
}


def calculate_opportunity_score(
    demand: float,
    readiness: float,
    regulatory: float,
    investment: float,
    competition: float,
) -> float:
    """Calculate overall opportunity score (0-100).

    Formula: (demand + readiness + regulatory + investment) / 4 - competition_adjustment

    Competition adjustment: subtract up to 25 points based on competition level.
    """
    avg_drivers = (demand + readiness + regulatory + investment) / 4

    # Competition: low competition = 0 penalty, high competition = 25 penalty
    competition_penalty = min(25, competition * 0.25)

    score = avg_drivers - competition_penalty
    return max(0, min(100, score))  # Clamp to 0-100


class PipelineOpportunityAgent(BaseAgent):
    """Analyzes pipeline company data to identify market opportunities.

    Uses scoring model to rank opportunities:
    - Market Demand (0-100)
    - Technology Readiness (0-100)
    - Regulatory Pressure (0-100)
    - Investment Interest (0-100)
    - Competition Level (0-100)

    Final Score = (sum of drivers / 4) - competition penalty
    """

    @property
    def name(self) -> str:
        return "pipeline_opportunity"

    def _calculate_opportunity_score(self, tech_gap: str, existing_competitors: int) -> dict:
        """Calculate opportunity scores for a technology gap."""
        # Get base scores from MARKET_DRIVERS
        drivers = MARKET_DRIVERS.get(tech_gap, {"demand": 60, "readiness": 60, "regulatory": 60, "investment": 60})
        base_competition = COMPETITION_LEVELS.get(tech_gap, 50)

        # Adjust competition based on competitor count
        # More competitors = higher competition score
        competitor_adjustment = min(30, existing_competitors * 5)
        competition_score = min(95, base_competition + competitor_adjustment)

        # Calculate drivers
        market_demand = drivers["demand"]
        technology_readiness = drivers["readiness"]
        regulatory_pressure = drivers["regulatory"]
        investment_interest = drivers["investment"]

        # Calculate overall score
        opportunity_score = calculate_opportunity_score(
            market_demand,
            technology_readiness,
            regulatory_pressure,
            investment_interest,
            competition_score,
        )

        return {
            "market_demand": market_demand,
            "technology_readiness": technology_readiness,
            "regulatory_pressure": regulatory_pressure,
            "investment_interest": investment_interest,
            "competition_score": competition_score,
            "opportunity_score": opportunity_score,
            "confidence": 0.7 + (existing_competitors == 0) * 0.2,  # Higher confidence for blue ocean
        }

    def _get_competition_label(self, score: float) -> str:
        """Convert competition score to label."""
        if score < 40:
            return "low"
        elif score < 70:
            return "medium"
        else:
            return "high"

    def execute(self, upstream_results=None) -> AgentResult:
        """Analyze pipeline data and identify opportunities."""
        conn = get_connection()
        schema.init_schema(conn)

        try:
            opportunities = self._analyze_opportunities(conn)
            inserted = self._insert_opportunities(conn, opportunities)

            _logger.info(
                "PipelineOpportunityAgent: identified %d new opportunities",
                inserted,
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "opportunities_identified": len(opportunities),
                    "opportunities_inserted": inserted,
                    "opportunity_types": list(set(o["opportunity_type"] for o in opportunities)),
                },
            )
        finally:
            conn.close()

    def _analyze_opportunities(self, conn) -> list[dict]:
        """Analyze pipeline data to identify opportunities."""
        opportunities = []

        # 1. Check for technology gaps
        tech_gap_opps = self._find_technology_gaps(conn)
        opportunities.extend(tech_gap_opps)

        # 2. Find failed companies with revival potential
        revival_opps = self._find_revivial_candidates(conn)
        opportunities.extend(revival_opps)

        # 3. Find market needs
        market_opps = self._find_market_needs(conn)
        opportunities.extend(market_opps)

        return opportunities

    def _find_technology_gaps(self, conn) -> list[dict]:
        """Identify technology areas with limited competition."""
        opportunities = []

        # Check which tech gaps already have companies
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT technology_focus FROM pipeline_companies WHERE company_type = 'active'")
        existing_techs = set()
        for row in cursor.fetchall():
            if row["technology_focus"]:
                for tech in row["technology_focus"].split(","):
                    existing_techs.add(tech.strip().lower())
        cursor.close()

        for tech_gap, description in TECH_GAPS.items():
            # Check if this technology gap is underserved
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*) as cnt FROM pipeline_companies
                   WHERE company_type = 'active'
                   AND technology_focus LIKE %s""",
                (f"%{tech_gap}%",),
            )
            count = cursor.fetchone()["cnt"]
            cursor.close()

            # Get scores for this tech gap
            scores = self._calculate_opportunity_score(tech_gap, count)

            opportunity = {
                "opportunity_type": "technology_gap",
                "pipeline_category": self._tech_to_category(tech_gap),
                "title": f"Opportunity: {tech_gap.replace('_', ' ').title()}",
                "description": description,
                "market_size_estimate": self._estimate_market_size(tech_gap),
                "entry_barriers": self._get_barriers(tech_gap),
                "competition_level": self._get_competition_label(scores["competition_score"]),
                "competition_score": scores["competition_score"],
                "market_demand_score": scores["market_demand"],
                "technology_readiness": scores["technology_readiness"],
                "regulatory_pressure": scores["regulatory_pressure"],
                "investment_interest": scores["investment_interest"],
                "opportunity_score": scores["opportunity_score"],
                "investment_needed": self._estimate_investment(tech_gap),
                "confidence_score": scores["confidence"],
                "source_data": json.dumps({"tech_gap": tech_gap, "existing_competitors": count}),
            }
            opportunities.append(opportunity)

        return opportunities

    def _find_revivial_candidates(self, conn) -> list[dict]:
        """Find failed companies that could be revived with updated technology."""
        opportunities = []

        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, name, technology_focus, description, year_shutdown
               FROM pipeline_companies
               WHERE company_type = 'failed'
               AND technology_focus IS NOT NULL
               ORDER BY year_shutdown DESC
               LIMIT 5"""
        )
        failed = cursor.fetchall()
        cursor.close()

        for company in failed:
            # Check if there's renewed demand for their technology
            tech = company["technology_focus"]

            opportunity = {
                "opportunity_type": "revival_candidate",
                "pipeline_category": self._tech_to_category(tech),
                "title": f"Revival: {company['name']}",
                "description": f"Update {company['name']}'s {tech} technology for modern pipeline operations. "
                              f"The company failed in {company['year_shutdown']} but the underlying technology "
                              f"addresses an ongoing market need.",
                "market_size_estimate": self._estimate_market_size(tech),
                "entry_barriers": "Requires domain expertise, potential IP issues",
                "competition_level": "low",
                "investment_needed": "$10-30M to restart operations",
                "confidence_score": 0.6,
                "related_company_id": company["id"],
                "source_data": json.dumps({
                    "original_company": company["name"],
                    "year_shutdown": company["year_shutdown"],
                    "technology": tech,
                }),
            }
            opportunities.append(opportunity)

        return opportunities

    def _find_market_needs(self, conn) -> list[dict]:
        """Identify underserved market segments."""
        opportunities = []

        # Check market segments with few players
        segments = ["water", "wastewater", "hydrogen", "carbon_capture"]
        target_segments = ["water", "wastewater", "hydrogen"]

        for segment in target_segments:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*) as cnt FROM pipeline_companies
                   WHERE company_type = 'active'
                   AND market_segment LIKE %s""",
                (f"%{segment}%",),
            )
            count = cursor.fetchone()["cnt"]
            cursor.close()

            if count < 3:
                segment_title = segment.title()
                opportunity = {
                    "opportunity_type": "market_need",
                    "pipeline_category": self._segment_to_category(segment),
                    "title": f"Opportunity: {segment_title} Pipeline Infrastructure",
                    "description": f"Growing demand for {segment_title.lower()} pipelines with limited competition. "
                                  f"Modernization and new construction create opportunities for inspection and monitoring solutions.",
                    "market_size_estimate": f"${count * 200}M+ annually in inspection services",
                    "entry_barriers": f"Regulatory requirements for {segment_title.lower()} infrastructure",
                    "competition_level": "low",
                    "investment_needed": "$5-15M for initial market entry",
                    "confidence_score": 0.7,
                    "source_data": json.dumps({"segment": segment, "current_players": count}),
                }
                opportunities.append(opportunity)

        return opportunities

    def _insert_opportunities(self, conn, opportunities: list[dict]) -> int:
        """Insert new opportunities into database, avoiding duplicates."""
        inserted = 0

        cursor = conn.cursor()
        for opp in opportunities:
            # Check if similar opportunity exists
            cursor.execute(
                """SELECT 1 FROM pipeline_opportunities
                   WHERE title = %s AND opportunity_type = %s LIMIT 1""",
                (opp["title"], opp["opportunity_type"]),
            )
            if cursor.fetchone():
                continue

            cursor.execute(
                """INSERT INTO pipeline_opportunities
                   (opportunity_type, pipeline_category, title, description,
                    market_size_estimate, entry_barriers, competition_level, competition_score,
                    market_demand_score, technology_readiness, regulatory_pressure, investment_interest,
                    opportunity_score,
                    investment_needed, confidence_score, related_company_id, source_data)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    opp["opportunity_type"],
                    opp["pipeline_category"],
                    opp["title"],
                    opp["description"],
                    opp.get("market_size_estimate"),
                    opp.get("entry_barriers"),
                    opp.get("competition_level", "medium"),
                    opp.get("competition_score"),
                    opp.get("market_demand_score"),
                    opp.get("technology_readiness"),
                    opp.get("regulatory_pressure"),
                    opp.get("investment_interest"),
                    opp.get("opportunity_score"),
                    opp.get("investment_needed"),
                    opp.get("confidence_score", 0.5),
                    opp.get("related_company_id"),
                    opp.get("source_data"),
                ),
            )
            inserted += 1

        conn.commit()
        cursor.close()
        return inserted

    def _tech_to_category(self, tech: str) -> str:
        """Map technology to pipeline category."""
        mapping = {
            "smart_pigging": "inspection",
            "leak_detection": "monitoring",
            "corrosion": "management",
            "digital_twin": "management",
            "robotic": "inspection",
            "ai_interpretation": "inspection",
            "edge": "monitoring",
            "hydrogen": "infrastructure",
        }
        tech_lower = tech.lower()
        for key, category in mapping.items():
            if key in tech_lower:
                return category
        return "management"

    def _segment_to_category(self, segment: str) -> str:
        """Map market segment to pipeline category."""
        mapping = {
            "water": "infrastructure",
            "wastewater": "infrastructure",
            "hydrogen": "infrastructure",
            "carbon": "management",
        }
        return mapping.get(segment, "management")

    def _estimate_market_size(self, tech: str) -> str:
        """Estimate market size for a technology."""
        estimates = {
            "smart_pigging": "$800M+ annually",
            "leak_detection": "$1.2B+ annually",
            "corrosion": "$600M+ annually",
            "digital_twin": "$500M+ annually",
            "robotic": "$400M+ annually",
            "hydrogen": "$300M+ by 2030",
            "ai_interpretation": "$700M+ annually",
            "edge": "$300M+ annually",
        }
        for key, size in estimates.items():
            if key in tech.lower():
                return size
        return "$100-500M+"

    def _get_barriers(self, tech: str) -> str:
        """Get entry barriers for a technology."""
        barriers = {
            "smart_pigging": "Technical certification, pig availability, operator relationships",
            "leak_detection": "Sensor accuracy, false positive rates, integration complexity",
            "corrosion": "Domain expertise, cathodic protection knowledge",
            "digital_twin": "Data access, model accuracy, operator trust",
            "robotic": "Hardware reliability, navigation in pipes, certification",
            "hydrogen": "Material compatibility, certification requirements",
            "ai_interpretation": "Training data availability, regulatory acceptance",
            "edge": "Ruggedized hardware, connectivity in remote areas",
        }
        for key, barrier in barriers.items():
            if key in tech.lower():
                return barrier
        return "Technical expertise, capital requirements"

    def _estimate_investment(self, tech: str) -> str:
        """Estimate investment needed for a technology startup."""
        estimates = {
            "smart_pigging": "$15-50M",
            "leak_detection": "$10-30M",
            "corrosion": "$5-15M",
            "digital_twin": "$20-60M",
            "robotic": "$25-75M",
            "hydrogen": "$30-100M",
            "ai_interpretation": "$10-25M",
            "edge": "$8-20M",
        }
        for key, investment in estimates.items():
            if key in tech.lower():
                return investment
        return "$10-30M"


if __name__ == "__main__":
    from config import setup_logging, load_config

    setup_logging()
    load_config()

    agent = PipelineOpportunityAgent()
    result = agent.execute()
    print(f"Agent result: {result.status}")
    print(f"Data: {result.data}")