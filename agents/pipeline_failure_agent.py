"""Pipeline Failure Analysis Agent - analyzes failed companies to identify patterns and opportunities."""

import json
import logging
from collections import Counter
from datetime import datetime

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


# Failure pattern categories
FAILURE_PATTERNS = {
    "cost_structure": {
        "keywords": ["cost", "expensive", "price", "margin", "capital", "burn"],
        "description": "Failed due to unsustainable cost structure or pricing challenges",
    },
    "timing": {
        "keywords": ["early", "late", "premature", "market timing", "ahead of time"],
        "description": "Failed due to market timing - too early or too late to market",
    },
    "technology": {
        "keywords": ["technology", "technical", "hardware", "software", "integration", "accuracy"],
        "description": "Failed due to technology challenges, reliability, or integration issues",
    },
    "market_adoption": {
        "keywords": ["adoption", "customer", "sales", "market fit", "demand", "competition"],
        "description": "Failed to achieve market adoption or customer traction",
    },
    "funding": {
        "keywords": ["ran out", "funding", "investor", "capital", "cash", "financing"],
        "description": "Failed due to insufficient funding or investor relations",
    },
    "regulatory": {
        "keywords": ["regulatory", "certification", "approval", "compliance", "standard"],
        "description": "Failed due to regulatory barriers or certification requirements",
    },
    "competitive": {
        "keywords": ["competition", "competitor", "market share", "differentiation"],
        "description": "Failed to compete effectively against established players",
    },
}


class PipelineFailureAgent(BaseAgent):
    """Analyzes pipeline company failures to identify patterns and revival opportunities.

    Identifies:
    - Common failure reasons by category
    - Hardware vs software failure patterns
    - Market adoption challenges
    - Technology timing issues
    - Funding problems

    Generates:
    - Pipeline Failure Report with insights
    - Revival opportunity recommendations
    - Lessons learned
    """

    @property
    def name(self) -> str:
        return "pipeline_failure_agent"

    def execute(self, upstream_results=None) -> AgentResult:
        """Execute failure analysis."""
        conn = get_connection()
        schema.init_schema(conn)

        try:
            # Analyze failure patterns
            patterns = self._analyze_failure_patterns(conn)

            # Analyze by type (hardware vs software)
            hw_sw_analysis = self._analyze_hw_sw_patterns(conn)

            # Analyze by category
            category_analysis = self._analyze_by_pipeline_category(conn)

            # Generate recommendations
            recommendations = self._generate_recommendations(patterns, hw_sw_analysis, category_analysis)

            # Store analysis results
            self._store_analysis(conn, "failure_pattern_overview", patterns, recommendations)

            self._store_analysis(conn, "hardware_vs_software", hw_sw_analysis)

            for category, analysis in category_analysis.items():
                self._store_analysis(conn, "category_analysis", analysis, None, category)

            _logger.info("PipelineFailureAgent: Analysis complete")

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "patterns_identified": len(patterns),
                    "hw_sw_analysis": hw_sw_analysis,
                    "category_count": len(category_analysis),
                    "recommendations_count": len(recommendations),
                },
            )
        finally:
            conn.close()

    def _analyze_failure_patterns(self, conn) -> dict:
        """Analyze overall failure patterns."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, failure_reason, pipeline_type, technology_focus,
                   funding_raised_usd, year_shutdown
            FROM pipeline_companies
            WHERE company_type = 'failed' AND failure_reason IS NOT NULL
        """)
        failed_companies = cursor.fetchall()
        cursor.close()

        if not failed_companies:
            return {"summary": "No failed companies to analyze", "patterns": []}

        patterns = {
            "total_failed": len(failed_companies),
            "by_cause": {},
            "by_technology": {},
            "avg_funding_lost": 0,
            "patterns": [],
        }

        # Categorize failures by cause
        cause_counter = Counter()
        tech_failure_map = {}

        total_funding = 0

        for company in failed_companies:
            reason = company["failure_reason"] or ""
            reason_lower = reason.lower()

            total_funding += company["funding_raised_usd"] or 0

            # Categorize by cause
            for pattern_name, pattern_info in FAILURE_PATTERNS.items():
                for keyword in pattern_info["keywords"]:
                    if keyword in reason_lower:
                        cause_counter[pattern_name] += 1
                        break

            # Map technology to failure
            tech = company["pipeline_type"] or "unknown"
            if tech not in tech_failure_map:
                tech_failure_map[tech] = []
            tech_failure_map[tech].append(reason[:100])

        patterns["avg_funding_lost"] = total_funding / len(failed_companies) if failed_companies else 0

        # Build cause breakdown
        for cause, count in cause_counter.most_common(5):
            patterns["by_cause"][cause] = {
                "count": count,
                "pct": round(count / len(failed_companies) * 100, 1),
                "description": FAILURE_PATTERNS.get(cause, {}).get("description", ""),
            }

        # Build patterns list
        for cause, data in patterns["by_cause"].items():
            patterns["patterns"].append({
                "type": cause,
                "count": data["count"],
                "percentage": data["pct"],
                "description": data["description"],
                "recommendation": self._get_recommendation_for_cause(cause),
            })

        return patterns

    def _analyze_hw_sw_patterns(self, conn) -> dict:
        """Analyze hardware vs software failure patterns."""
        cursor = conn.cursor()

        # Define hardware and software technologies
        hw_techs = ["infrastructure", "inspection", "robotics"]
        sw_techs = ["management", "monitoring", "digital"]

        hw_patterns = {"failure_reasons": [], "count": 0, "avg_funding": 0}
        sw_patterns = {"failure_reasons": [], "count": 0, "avg_funding": 0}

        for company in cursor.execute("""
            SELECT pipeline_type, failure_reason, funding_raised_usd
            FROM pipeline_companies
            WHERE company_type = 'failed'
        """):
            reason = company["failure_reason"] or ""
            pt = company["pipeline_type"] or ""

            if pt in hw_techs:
                hw_patterns["failure_reasons"].append(reason[:100])
                hw_patterns["count"] += 1
                hw_patterns["avg_funding"] += company["funding_raised_usd"] or 0
            elif pt in sw_techs:
                sw_patterns["failure_reasons"].append(reason[:100])
                sw_patterns["count"] += 1
                sw_patterns["avg_funding"] += company["funding_raised_usd"] or 0

        cursor.close()

        if hw_patterns["count"] > 0:
            hw_patterns["avg_funding"] /= hw_patterns["count"]
        if sw_patterns["count"] > 0:
            sw_patterns["avg_funding"] /= sw_patterns["count"]

        return {
            "hardware": hw_patterns,
            "software": sw_patterns,
            "insight": self._generate_hw_sw_insight(hw_patterns, sw_patterns),
        }

    def _analyze_by_pipeline_category(self, conn) -> dict:
        """Analyze failures by pipeline category."""
        cursor = conn.cursor()

        analysis = {}

        for category in ["inspection", "monitoring", "management", "infrastructure"]:
            cursor.execute("""
                SELECT COUNT(*) as cnt,
                       AVG(funding_raised_usd) as avg_funding,
                       GROUP_CONCAT(failure_reason SEPARATOR '|') as reasons
                FROM pipeline_companies
                WHERE company_type = 'failed' AND pipeline_type = %s
            """, (category,))

            row = cursor.fetchone()
            if row and row["cnt"] > 0:
                reasons = (row["reasons"] or "").split("|")
                analysis[category] = {
                    "count": row["cnt"],
                    "avg_funding_lost": row["avg_funding"] or 0,
                    "common_reasons": Counter(reasons).most_common(3),
                }

        cursor.close()
        return analysis

    def _generate_recommendations(self, patterns: dict, hw_sw: dict, categories: dict) -> list[dict]:
        """Generate revival recommendations based on analysis."""
        recommendations = []

        # For each failure pattern, suggest a revival approach
        for pattern in patterns.get("patterns", []):
            cause = pattern["type"]

            if cause == "cost_structure":
                recommendations.append({
                    "type": cause,
                    "title": "Reduce Capital Intensity",
                    "description": "Use software-as-a-service model, lease equipment, partner with established players",
                    "target": "Any pipeline technology category",
                    "confidence": 0.8,
                })

            elif cause == "timing":
                recommendations.append({
                    "type": cause,
                    "title": "Wait for Market Maturity",
                    "description": "Re-evaluate with today's AI capabilities, IoT sensors, and cloud infrastructure",
                    "target": "Digital twins, predictive maintenance",
                    "confidence": 0.7,
                })

            elif cause == "market_adoption":
                recommendations.append({
                    "type": cause,
                    "title": "Start with Pilot Programs",
                    "description": "Proof of concept with major operator, then scale. Focus on guaranteed ROI",
                    "target": "Inspection, monitoring technologies",
                    "confidence": 0.85,
                })

            elif cause == "technology":
                recommendations.append({
                    "type": cause,
                    "title": "Focus on Integration",
                    "description": "Build pre-built integrations with major SCADA and ERP systems",
                    "target": "Software and analytics platforms",
                    "confidence": 0.75,
                })

            elif cause == "funding":
                recommendations.append({
                    "type": cause,
                    "title": "Target Strategic Investors",
                    "description": "Seek funding from oil & gas majors, not pure VC funds",
                    "target": "Hardware and specialized software",
                    "confidence": 0.7,
                })

        return recommendations

    def _generate_hw_sw_insight(self, hw: dict, sw: dict) -> str:
        """Generate insight comparing hardware vs software failures."""
        insight_parts = []

        if hw["count"] > sw["count"]:
            insight_parts.append(
                f"Hardware companies are more likely to fail ({hw['count']} vs {sw['count']}) "
                f"with avg funding lost of ${hw['avg_funding']:,.0f} vs ${sw['avg_funding']:,.0f}."
            )
        elif sw["count"] > hw["count"]:
            insight_parts.append(
                f"Software companies show higher failure rates ({sw['count']} vs {hw['count']})."
            )
        else:
            insight_parts.append("Hardware and software failure rates are similar.")

        return " ".join(insight_parts)

    def _get_recommendation_for_cause(self, cause: str) -> str:
        """Get recommendation text for failure cause."""
        recommendations = {
            "cost_structure": "Use asset-light models, partnerships, or subscription pricing",
            "timing": "Reassess market readiness, consider pivoting to adjacent markets",
            "technology": "Partner with established players for distribution and integration",
            "market_adoption": "Start with pilot programs, focus on proven ROI",
            "funding": "Seek strategic investors from the oil & gas industry",
            "regulatory": "Build compliance team early, seek certifications proactively",
            "competitive": "Focus on niche verticals or specific pipeline types",
        }
        return recommendations.get(cause, "Consider strategic partnerships")

    def _store_analysis(self, conn, analysis_type: str, data: dict,
                       recommendations: list = None, category: str = None) -> None:
        """Store analysis results in database."""
        cursor = conn.cursor()

        insight_json = json.dumps(data)
        rec_json = json.dumps(recommendations) if recommendations else None

        # Count patterns
        pattern_count = len(data.get("patterns", [])) if isinstance(data, dict) else 0

        cursor.execute("""
            INSERT INTO pipeline_failure_analysis
            (analysis_type, category, insight_json, pattern_count, confidence, recommendation_json)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                insight_json = VALUES(insight_json),
                pattern_count = VALUES(pattern_count),
                confidence = VALUES(confidence),
                recommendation_json = VALUES(recommendation_json),
                analyzed_at = NOW()
        """, (analysis_type, category, insight_json, pattern_count, 0.7, rec_json))

        conn.commit()
        cursor.close()


def generate_failure_report(conn) -> str:
    """Generate a human-readable failure analysis report."""
    cursor = conn.cursor()

    # Get all stored analyses
    cursor.execute("""
        SELECT analysis_type, category, insight_json, recommendation_json, analyzed_at
        FROM pipeline_failure_analysis
        ORDER BY analyzed_at DESC
    """)

    analyses = cursor.fetchall()
    cursor.close()

    if not analyses:
        return "No failure analysis available yet. Run the analysis agent first."

    report_lines = [
        "## Pipeline Company Failure Analysis Report",
        "",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d')}_",
        "",
        "---",
        "",
    ]

    for analysis in analyses:
        insight = json.loads(analysis["insight_json"])
        recs = json.loads(analysis["recommendation_json"]) if analysis["recommendation_json"] else []

        analysis_type = analysis["analysis_type"].replace("_", " ").title()

        if analysis["category"]:
            analysis_type += f" - {analysis['category'].title()}"

        report_lines.append(f"### {analysis_type}")
        report_lines.append("")

        # Summary
        if "total_failed" in insight:
            report_lines.append(f"- **{insight['total_failed']}** failed companies analyzed")
        if "avg_funding_lost" in insight:
            report_lines.append(f"- **Avg funding lost:** ${insight['avg_funding_lost']:,.0f}")

        # Top failure patterns
        if "by_cause" in insight and insight["by_cause"]:
            report_lines.append("")
            report_lines.append("#### Top Failure Patterns:")
            for cause, data in list(insight["by_cause"].items())[:5]:
                report_lines.append(f"- **{cause.replace('_', ' ').title()}**: {data['pct']}% ({data['count']} companies)")

        # Hardware vs Software insight
        if "insight" in insight:
            report_lines.append("")
            report_lines.append(f"**Key Insight:** {insight['insight']}")

        # Recommendations
        if recs:
            report_lines.append("")
            report_lines.append("#### Recommended Revival Approaches:")
            for rec in recs[:5]:
                report_lines.append(f"- **{rec['title']}**: {rec['description']}")

        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    return "\n".join(report_lines)


# CLI runner
if __name__ == "__main__":
    from config import setup_logging, load_config

    setup_logging()
    load_config()

    agent = PipelineFailureAgent()
    result = agent.execute()

    print(f"Agent result: {result.status}")
    print(f"Data: {result.data}")

    # Generate report
    from db.connection import get_connection
    conn = get_connection()
    report = generate_failure_report(conn)
    print("\n" + report[:2000])