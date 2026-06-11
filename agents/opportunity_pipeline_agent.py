"""Opportunity Pipeline Agent — cross-domain analysis producing ranked opportunities."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class OpportunityPipelineAgent(BaseAgent):
    """Cross-domain analysis that produces a ranked opportunity pipeline.

    Combines insights from:
    - Failed startups (what failed and why)
    - Revival industries (what's coming back)
    - Geographic hotspots (where to focus)
    - BLS survival rates (risk assessment)
    - News trends (market timing)

    Produces a prioritized list of actionable opportunities with scores.
    """

    @property
    def name(self) -> str:
        return "opportunity_pipeline"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}
        opportunities = []

        # 1. Load upstream analysis results if available
        upstream_data = {}
        if upstream_results:
            for r in upstream_results:
                if hasattr(r, "data"):
                    upstream_data[r.agent_name] = r.data

        # 2. Cross-reference: Failed manufacturing startups vs. Revival industries
        cursor = conn.cursor()
        cursor.execute(
            """SELECT fs.name, fs.manufacturing_sub_sector, fs.funding_raised_usd,
                      fs.failure_reason, fs.region, fs.year_shutdown,
                      ri.industry, ri.why_returning, ri.market_fit, ri.market_size_2030
               FROM failed_startups fs
               JOIN revival_industries ri ON (
                   fs.manufacturing_sub_sector LIKE CONCAT('%', ri.industry, '%')
                   OR ri.industry LIKE CONCAT('%', fs.manufacturing_sub_sector, '%')
               )
               WHERE fs.manufacturing_sub_sector IS NOT NULL
               ORDER BY fs.funding_raised_usd DESC
               LIMIT 20"""
        )
        revival_match = cursor.fetchall()
        cursor.close()

        for match in revival_match:
            m = dict(match)
            # Score this opportunity
            score = 0
            # Higher funding = bigger market was validated
            if m["funding_raised_usd"] and m["funding_raised_usd"] > 100_000_000:
                score += 25
            elif m["funding_raised_usd"] and m["funding_raised_usd"] > 50_000_000:
                score += 15
            elif m["funding_raised_usd"] and m["funding_raised_usd"] > 10_000_000:
                score += 10
            # Market fit confirmed
            if m["market_fit"]:
                score += 20
            # Clear market size
            if m["market_size_2030"]:
                score += 15
            # Capital or scale failure = revivable (not bad idea)
            reason = (m["failure_reason"] or "").lower()
            if "capital" in reason or "funding" in reason:
                score += 15
            if "scale" in reason or "pilot" in reason:
                score += 10
            # Recent failure = fresher data
            if m["year_shutdown"] and m["year_shutdown"] >= 2022:
                score += 10

            opportunities.append(
                {
                    "type": "revival_from_failure",
                    "startup": m["name"],
                    "sub_sector": m["manufacturing_sub_sector"],
                    "revival_industry": m["industry"],
                    "funding_lost": m["funding_raised_usd"],
                    "failure_reason": m["failure_reason"],
                    "region": m["region"],
                    "why_returning": m["why_returning"],
                    "market_size": m["market_size_2030"],
                    "opportunity_score": min(score, 100),
                    "risk_level": "low"
                    if score >= 60
                    else "medium"
                    if score >= 40
                    else "high",
                    "timing": "now"
                    if m["year_shutdown"] and m["year_shutdown"] >= 2022
                    else "wait",
                }
            )

        # 3. Geographic opportunities (high failure density + revival potential)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COALESCE(fs.region, fs.country) as area,
                      COUNT(DISTINCT fs.name) as failure_count,
                      GROUP_CONCAT(DISTINCT gh.revival_potential SEPARATOR ',') as revival_potential,
                      GROUP_CONCAT(DISTINCT ri.industry SEPARATOR ',') as matching_industries
               FROM failed_startups fs
               LEFT JOIN geographic_hotspots gh ON (
                   COALESCE(fs.region, fs.country) LIKE CONCAT('%', gh.region, '%')
                   OR gh.region LIKE CONCAT('%', COALESCE(fs.region, fs.country), '%')
               )
               LEFT JOIN revival_industries ri ON (
                   fs.manufacturing_sub_sector LIKE CONCAT('%', ri.industry, '%')
               )
               WHERE fs.manufacturing_sub_sector IS NOT NULL
               GROUP BY area
               HAVING failure_count >= 2
               ORDER BY failure_count DESC"""
        )
        geo_opp = cursor.fetchall()
        cursor.close()

        for g in geo_opp:
            gd = dict(g)
            score = 30 + min(gd["failure_count"] * 10, 40)
            if gd["revival_potential"]:
                score += 15
            if gd["matching_industries"]:
                score += 15
            opportunities.append(
                {
                    "type": "geographic_opportunity",
                    "region": gd["area"],
                    "failure_count": gd["failure_count"],
                    "revival_potential": gd["revival_potential"],
                    "matching_industries": gd["matching_industries"],
                    "opportunity_score": min(score, 100),
                    "risk_level": "low"
                    if score >= 60
                    else "medium"
                    if score >= 40
                    else "high",
                    "timing": "now",
                }
            )

        # 4. Whale-backing boost — load latest whale investor findings
        whale_sectors = set()
        whale_investors_by_sector: dict[str, list[str]] = {}
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT insights_json FROM analysis_whale_investors
                   ORDER BY analyzed_at DESC LIMIT 1"""
            )
            whale_row = cursor.fetchone()
            cursor.close()
            if whale_row:
                whale_data = json.loads(whale_row["insights_json"])
                for finding in whale_data.get("top_findings", []):
                    for sector in finding.get("sectors_mentioned", []):
                        s = sector.lower()
                        whale_sectors.add(s)
                        for inv in finding.get("investor_names", []):
                            whale_investors_by_sector.setdefault(s, [])
                            if inv not in whale_investors_by_sector[s]:
                                whale_investors_by_sector[s].append(inv)
        except Exception as e:
            _logger.warning("Could not load whale investor data for boost: %s", e)

        def opp_industry_text(o: dict) -> str:
            return " ".join(
                str(o.get(k) or "")
                for k in (
                    "sub_sector",
                    "revival_industry",
                    "matching_industries",
                    "industry",
                    "region",
                )
            ).lower()

        # Apply whale boost
        whale_boosted = 0
        for o in opportunities:
            o_text = opp_industry_text(o)
            matched_whale_sectors = []
            matched_whale_investors = []
            for ws in whale_sectors:
                if ws in o_text or any(w in o_text for w in ws.split()):
                    matched_whale_sectors.append(ws)
                    matched_whale_investors.extend(
                        whale_investors_by_sector.get(ws, [])
                    )
            if matched_whale_sectors:
                # Boost: +5 base, +5 if investors named, +5 if multiple sectors
                boost = 5
                if matched_whale_investors:
                    boost += 5
                if len(matched_whale_sectors) >= 2:
                    boost += 5
                old_score = o["opportunity_score"]
                o["opportunity_score"] = min(o["opportunity_score"] + boost, 100)
                # Re-derive risk level after boost
                s = o["opportunity_score"]
                o["risk_level"] = "low" if s >= 60 else "medium" if s >= 40 else "high"
                o["whale_backed"] = bool(matched_whale_investors)
                o["whale_sectors"] = matched_whale_sectors
                o["whale_investors"] = list(set(matched_whale_investors))
                if o["opportunity_score"] > old_score:
                    whale_boosted += 1

        # 5. Sort by score
        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

        # 5. Risk summary
        risk_summary = {
            "low_risk": sum(1 for o in opportunities if o["risk_level"] == "low"),
            "medium_risk": sum(1 for o in opportunities if o["risk_level"] == "medium"),
            "high_risk": sum(1 for o in opportunities if o["risk_level"] == "high"),
            "total_opportunities": len(opportunities),
        }
        insights["risk_summary"] = risk_summary
        insights["opportunities"] = opportunities[:30]  # Top 30
        insights["top_10"] = opportunities[:10]

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_opportunity_pipeline")
        cursor.execute(
            """INSERT INTO analysis_opportunity_pipeline
               (analysis_type, insights_json, analyzed_at, record_count)
               VALUES (%s, %s, %s, %s)""",
            (
                "opportunity_pipeline_full",
                json.dumps(insights, default=str),
                datetime.now(timezone.utc).isoformat(),
                len(opportunities),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        _logger.info(
            "OpportunityPipelineAgent: %d opportunities (%d low risk, %d whale-boosted)",
            len(opportunities),
            risk_summary["low_risk"],
            whale_boosted,
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "total_opportunities": len(opportunities),
                "low_risk": risk_summary["low_risk"],
                "medium_risk": risk_summary["medium_risk"],
                "top_opportunity": opportunities[0]["startup"]
                if opportunities and opportunities[0]["type"] == "revival_from_failure"
                else "N/A",
                "records_affected": len(opportunities),
                "top_insight": f"{len(opportunities)} opportunities found: {risk_summary['low_risk']} low risk, {risk_summary['medium_risk']} medium risk",
            },
        )
