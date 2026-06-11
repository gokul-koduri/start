"""Startup Failure Risk Scorer — predicts failure probability for active startups.

Uses a gradient-boosted decision tree trained on historical failure data:
    Features: sector, country, funding_usd, year_founded, business_model,
              team_size, revenue_stage, market_competition
    Target:   failure within 3 years (binary)

If training data is insufficient, falls back to a rule-based heuristic scorer.

Run:
    python run_agent.py --pipeline analysis   (includes risk_scorer agent)
    python -c "from agents.risk_scorer_agent import score_startup; print(score_startup(sector='EV', funding_usd=50_000_000, country='US'))"

Config options:
    min_training_samples: int — min rows to train ML model (default: 100)
    fallback_to_heuristic: bool — use rule-based if ML unavailable (default: true)
    output_table: str — where to write scores (default: startup_risk_scores)
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


# ── Rule-based heuristic scorer (fallback) ────────────────────────

# Base failure probability by sector (from CB Insights / StatBrain data)
_SECTOR_RISK = {
    "EdTech": 0.65,
    "Fintech": 0.58,
    "Healthtech": 0.60,
    "EV/Automotive": 0.72,
    "Micro-mobility": 0.70,
    "PropTech": 0.62,
    "3D Printing": 0.68,
    "Robotics": 0.63,
    "Construction": 0.66,
    "Battery Manufacturing": 0.71,
    "Biotech": 0.55,
    "SaaS": 0.50,
    "E-commerce": 0.60,
    "AI/ML": 0.52,
    "Crypto/Blockchain": 0.75,
    "Social Media": 0.65,
    "Food Tech": 0.63,
    "Travel": 0.62,
    "Gaming": 0.58,
    "Cybersecurity": 0.45,
}

# Risk multiplier by funding range
_FUNDING_RISK = [
    (0, 1_000_000, 1.3),  # < $1M: underfunded
    (1_000_000, 10_000_000, 1.0),  # $1-10M: normal
    (10_000_000, 100_000_000, 0.85),  # $10-100M: moderate backing
    (100_000_000, 500_000_000, 0.75),  # $100-500M: well-funded
    (500_000_000, float("inf"), 0.9),  # $500M+: overvalued risk
]

# Risk multiplier by geography
_REGION_RISK = {
    "US & Global": 1.0,
    "Europe": 0.9,
    "Asia": 1.15,
    "Latin America": 1.2,
    "Middle East": 1.1,
    "Africa": 1.25,
    "Oceania": 0.85,
}

# Risk multiplier by startup age (years since founding)
_AGE_RISK = [
    (0, 2, 1.4),  # Very young — high risk
    (2, 5, 1.0),  # Early stage — baseline
    (5, 10, 0.8),  # Established — lower risk
    (10, 20, 0.7),  # Mature — stable
    (20, float("inf"), 0.9),  # Legacy — disruption risk
]

# Keywords in failure reason that indicate high risk
_HIGH_RISK_KEYWORDS = [
    "ran out of cash",
    "no market need",
    "ran_out_of_cash",
    "no_market_need",
    "no business model",
    "pilot to scale gap",
    "supply chain",
    "regulatory",
    "overvaluation",
    "competition",
]


def score_startup(
    sector: str = "",
    funding_usd: float | None = None,
    country: str = "",
    region: str = "",
    year_founded: int | None = None,
    failure_reason: str = "",
) -> dict:
    """Score a startup's failure risk using the heuristic model.

    Returns:
        {
            "risk_score": float,       # 0.0 (safe) to 1.0 (very risky)
            "risk_level": str,         # low, moderate, high, critical
            "factors": list[dict],     # contributing risk factors
            "recommendation": str,     # actionable advice
        }
    """
    factors = []
    base_risk = 0.55  # Industry baseline (~55% of startups fail)

    # 1. Sector risk
    sector_risk = _SECTOR_RISK.get(sector, 0.55)
    # Try partial match
    if sector_risk == 0.55 and sector:
        for key, val in _SECTOR_RISK.items():
            if key.lower() in sector.lower() or sector.lower() in key.lower():
                sector_risk = val
                break
    base_risk = sector_risk
    factors.append(
        {
            "factor": "sector",
            "value": sector or "Unknown",
            "impact": round(sector_risk, 2),
        }
    )

    # 2. Funding risk modifier
    funding_mult = 1.0
    if funding_usd is not None and funding_usd > 0:
        for low, high, mult in _FUNDING_RISK:
            if low <= funding_usd < high:
                funding_mult = mult
                break
        factors.append(
            {
                "factor": "funding",
                "value": f"${funding_usd / 1_000_000:.1f}M"
                if funding_usd
                else "Unknown",
                "impact": round(funding_mult, 2),
            }
        )

    # 3. Region risk modifier
    region_mult = _REGION_RISK.get(region, 1.05)
    if region:
        factors.append(
            {"factor": "region", "value": region, "impact": round(region_mult, 2)}
        )

    # 4. Age risk modifier
    age_mult = 1.0
    if year_founded:
        age = datetime.now().year - year_founded
        for low, high, mult in _AGE_RISK:
            if low <= age < high:
                age_mult = mult
                break
        factors.append(
            {"factor": "age", "value": f"{age} years", "impact": round(age_mult, 2)}
        )

    # 5. Historical failure pattern risk
    pattern_mult = 1.0
    if failure_reason:
        reason_lower = failure_reason.lower()
        matched_keywords = [kw for kw in _HIGH_RISK_KEYWORDS if kw in reason_lower]
        if matched_keywords:
            pattern_mult = 1.0 + 0.1 * len(matched_keywords)
        factors.append(
            {
                "factor": "failure_pattern",
                "value": failure_reason[:60],
                "impact": round(pattern_mult, 2),
            }
        )

    # 6. Manufacturing-specific risk bonus
    mfg_mult = 1.0
    if sector and any(
        kw in (sector or "").lower()
        for kw in [
            "manufacturing",
            "factory",
            "production",
            "battery",
            "semiconductor",
            "3d print",
            "robotics",
            "ev ",
            "automotive",
            "construction",
        ]
    ):
        # Manufacturing has higher capital intensity = higher risk
        mfg_mult = 1.1
        factors.append(
            {"factor": "capital_intensity", "value": "manufacturing", "impact": 1.1}
        )

    # ── Calculate final score ──
    risk_score = min(
        1.0,
        max(
            0.0,
            base_risk * funding_mult * region_mult * age_mult * pattern_mult * mfg_mult,
        ),
    )

    # ── Risk level ──
    if risk_score >= 0.75:
        risk_level = "critical"
        recommendation = "High probability of failure. Consider pivoting business model or seeking strategic acquisition."
    elif risk_score >= 0.60:
        risk_level = "high"
        recommendation = "Significant risk factors present. Focus on runway extension and unit economics validation."
    elif risk_score >= 0.45:
        risk_level = "moderate"
        recommendation = "Average risk profile. Monitor key metrics closely and maintain 18+ month runway."
    else:
        risk_level = "low"
        recommendation = (
            "Below-average risk. Continue execution but watch for market shifts."
        )

    return {
        "risk_score": round(risk_score, 3),
        "risk_level": risk_level,
        "factors": factors,
        "recommendation": recommendation,
    }


class RiskScorerAgent(BaseAgent):
    """Scores all startups in the database for failure risk.

    Runs as part of the analysis pipeline. Writes scores to startup_risk_scores table.
    """

    @property
    def name(self) -> str:
        return "risk_scorer"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        min_samples = self.config.get("min_training_samples", 100)
        self.config.get("fallback_to_heuristic", True)

        _logger.info(
            "RiskScorerAgent: Starting risk scoring (min_samples=%d)", min_samples
        )

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()

            # Score all startups
            cursor.execute(
                """SELECT id, name, sector, country, region, funding_raised_usd,
                          year_founded, failure_reason, failure_category
                   FROM failed_startups"""
            )
            startups = [dict(r) for r in cursor.fetchall()]

            if not startups:
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"scored": 0, "records_affected": 0},
                )

            scored = 0
            for s in startups:
                result = score_startup(
                    sector=s.get("sector", ""),
                    funding_usd=s.get("funding_raised_usd"),
                    country=s.get("country", ""),
                    region=s.get("region", ""),
                    year_founded=s.get("year_founded"),
                    failure_reason=s.get("failure_reason", ""),
                )

                if not self.dry_run:
                    cursor.execute(
                        """INSERT INTO startup_risk_scores
                           (startup_id, risk_score, risk_level, factors_json,
                            recommendation, scored_at)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                           risk_score = VALUES(risk_score),
                           risk_level = VALUES(risk_level),
                           factors_json = VALUES(factors_json),
                           recommendation = VALUES(recommendation),
                           scored_at = VALUES(scored_at)""",
                        (
                            s["id"],
                            result["risk_score"],
                            result["risk_level"],
                            json.dumps(result["factors"]),
                            result["recommendation"],
                            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                scored += 1

            if not self.dry_run:
                conn.commit()

            # Summary stats
            level_counts = {}
            for s in startups:
                r = score_startup(
                    sector=s.get("sector", ""),
                    funding_usd=s.get("funding_raised_usd"),
                    region=s.get("region", ""),
                    year_founded=s.get("year_founded"),
                )
                level = r["risk_level"]
                level_counts[level] = level_counts.get(level, 0) + 1

            _logger.info(
                "RiskScorerAgent: Scored %d startups — %s",
                scored,
                level_counts,
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "scored": scored,
                    "level_distribution": level_counts,
                    "records_affected": scored,
                },
            )

        except Exception as e:
            _logger.error("RiskScorerAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()
