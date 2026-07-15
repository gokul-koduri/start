"""
Manufacturing Opportunity Scoring Engine — Phase v2.

Implements the four scoring models from the Manufacturing Opportunity Intelligence Platform:

  A) Manufacturing Opportunity Score  — "Should this company exist?"
  B) Revival Score                    — "Could this failed company succeed today?"
  C) Regional Fit Score               — "Where should this company be built?"
  D) Founder Fit Score                — "Who should build this company?"

Formulas and weights are defined in the implementation plan.
All scores are 0-100 unless otherwise noted.
All confidence scores are 0-1.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import pymysql


_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_VERSION = "v2.0.0"
SCORE_DECISION_THRESHOLD_STRONG = 75
SCORE_DECISION_THRESHOLD_WEAK = 60
SCORE_DECISION_THRESHOLD_VALIDATE = 45


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def compute_confidence(
    data_completeness: float | int,   # 0-1
    source_reliability: float | int,   # 0-1
    evidence_count: int = 0,
) -> float:
    """Compute overall confidence score for an opportunity.

    Args:
        data_completeness: % of required fields populated (0-1)
        source_reliability: Average reliability of data sources (0-1)
        evidence_count: Number of supporting signals/events (0 = lowest)

    Returns:
        float: Combined confidence score (0-1)
    """
    # Evidence count contribution: diminishing returns, max 30% impact
    evidence_factor = min(1.0, evidence_count / 10.0) * 0.3

    confidence = (
        data_completeness * 0.4 +
        source_reliability * 0.3 +
        evidence_factor
    )
    return round(min(1.0, max(0.0, confidence)), 3)


# ---------------------------------------------------------------------------
# A) Manufacturing Opportunity Score
# ---------------------------------------------------------------------------

def compute_opportunity_score(
    demand_score: float,           # 0-100
    gap_score: float,             # 0-100
    feasibility_score: float,      # 0-100
    timing_score: float,           # 0-100
    competition_score: float,      # 0-100  (higher = more competition = BAD)
) -> dict[str, float]:
    """Compute the Manufacturing Opportunity Score.

    Question: "Should this company exist?"

    Formula:
        Opportunity_Score =
            demand_score     * 0.25 +
            gap_score        * 0.25 +
            feasibility_score * 0.20 +
            timing_score     * 0.15 +
            (100 - competition_score) * 0.15

    Decision thresholds:
        >= 75  Strong recommendation
        60-74  Conditional recommendation
        45-59  Requires validation
        < 45   Not recommended (deprioritize)

    Args:
        demand_score:       Market demand 0-100
        gap_score:          Supply gap / domestic shortage 0-100
        feasibility_score:  Manufacturing feasibility 0-100
        timing_score:       Policy/technology/market window 0-100
        competition_score:  Competition intensity 0-100 (higher = worse)

    Returns:
        dict with keys:
            opportunity_score (0-100), demand_component, gap_component,
            feasibility_component, timing_component, competition_component,
            decision (strong_conditional_requires_validate_not_recommended)
    """
    demand_c = demand_score * 0.25
    gap_c = gap_score * 0.25
    feasibility_c = feasibility_score * 0.20
    timing_c = timing_score * 0.15
    competition_c = (100 - min(100, max(0, competition_score))) * 0.15

    total = demand_c + gap_c + feasibility_c + timing_c + competition_c
    total = round(min(100.0, max(0.0, total)), 1)

    # Determine decision
    if total >= SCORE_DECISION_THRESHOLD_STRONG:
        decision = "strong_recommendation"
    elif total >= SCORE_DECISION_THRESHOLD_WEAK:
        decision = "conditional_recommendation"
    elif total >= SCORE_DECISION_THRESHOLD_VALIDATE:
        decision = "requires_validation"
    else:
        decision = "not_recommended"

    return {
        "opportunity_score": total,
        "demand_component": round(demand_c, 2),
        "gap_component": round(gap_c, 2),
        "feasibility_component": round(feasibility_c, 2),
        "timing_component": round(timing_c, 2),
        "competition_component": round(competition_c, 2),
        "decision": decision,
    }


# ---------------------------------------------------------------------------
# B) Revival Score
# ---------------------------------------------------------------------------

def compute_revial_score(
    failure_addressed: float,      # 0-100: Original failure reason resolved?
    market_change: float,          # 0-100: Demand/pricing improvement
    tech_change: float,             # 0-100: New capabilities, process improvements
    cost_change: float,             # 0-100: Input cost reduction, efficiency gains
    policy_change: float,           # 0-100: Incentives, trade policy, etc.
    original_failure_severity: float = 1.0,  # 0-1 (1=major, 0=minor)
    years_since_failure: int = 0,          # Affects asset availability
) -> dict[str, float]:
    """Compute the Revival Score.

    Question: "Could this failed company succeed today?"

    Formula:
        Revival_Score =
            failure_addressed * 0.30 +
            market_change     * 0.25 +
            tech_change       * 0.20 +
            cost_change       * 0.15 +
            policy_change     * 0.10

    Additional multipliers:
        - Original failure severity: Major failures need higher scores to overcome
        - Years since failure: > 7 years reduces score (assets may be unavailable)

    Args:
        failure_addressed: Is original failure reason resolved? (0-100)
        market_change:     Market conditions improvement (0-100)
        tech_change:       Technology advances relevant to original failure (0-100)
        cost_change:       Cost structure improvements (0-100)
        policy_change:     Policy tailwinds (0-100)
        original_failure_severity: How severe was the failure? (0-1)
        years_since_failure: Years since the company failed

    Returns:
        dict with keys: revival_score (0-100), components, multipliers,
            decision
    """
    failure_c = failure_addressed * 0.30
    market_c = market_change * 0.25
    tech_c = tech_change * 0.20
    cost_c = cost_change * 0.15
    policy_c = policy_change * 0.10

    total = failure_c + market_c + tech_c + cost_c + policy_c

    # Apply severity multiplier (major failures require higher base score)
    # Severity multiplier: 1.0 (minor) to 0.7 (catastrophic)
    severity_multiplier = 1.0 - (original_failure_severity * 0.3)
    total *= severity_multiplier

    # Asset availability penalty (> 7 years = significant asset depreciation)
    if years_since_failure > 10:
        total *= 0.6
    elif years_since_failure > 7:
        total *= 0.8
    elif years_since_failure > 5:
        total *= 0.9

    total = round(min(100.0, max(0.0, total)), 1)

    # Decide classification
    if total >= 70:
        decision = "strong_revival_candidate"
    elif total >= 50:
        decision = "conditional_revival"
    elif total >= 30:
        decision = "low_priority_revival"
    else:
        decision = "not_viable_revivial"

    return {
        "revival_score": total,
        "failure_component": round(failure_c, 2),
        "market_component": round(market_c, 2),
        "tech_component": round(tech_c, 2),
        "cost_component": round(cost_c, 2),
        "policy_component": round(policy_c, 2),
        "severity_multiplier": round(severity_multiplier, 3),
        "years_penalty_applied": years_since_failure > 5,
        "decision": decision,
    }


# ---------------------------------------------------------------------------
# C) Regional Fit Score
# ---------------------------------------------------------------------------

def compute_regional_fit_score(
    workforce_score: float,              # 0-100
    infrastructure_score: float,        # 0-100
    supplier_score: float,              # 0-100
    energy_score: float,               # 0-100
    incentive_score: float,              # 0-100
    logistics_score: float = 50.0,     # 0-100
) -> dict[str, float]:
    """Compute the Regional Fit Score.

    Question: "Where should this company be built?"

    Formula:
        Regional_Fit =
            workforce_score       * 0.25 +
            infrastructure_score  * 0.20 +
            supplier_score        * 0.20 +
            energy_score          * 0.15 +
            incentive_score       * 0.10 +
            logistics_score       * 0.10

    Args:
        workforce_score:      Skills availability, wage rates, training (0-100)
        infrastructure_score: Facilities, utilities, zoning, permitting (0-100)
        supplier_score:       Proximity to materials, sub-suppliers (0-100)
        energy_score:         Electricity rates, natural gas, renewables (0-100)
        incentive_score:      Tax credits, grants, training subsidies (0-100)
        logistics_score:      Port access, highway/rail, customer proximity (0-100)

    Returns:
        dict with regional_fit_score and component breakdown (0-100)
    """
    total = (
        workforce_score * 0.25 +
        infrastructure_score * 0.20 +
        supplier_score * 0.20 +
        energy_score * 0.15 +
        incentive_score * 0.10 +
        logistics_score * 0.10
    )
    total = round(min(100.0, max(0.0, total)), 1)

    return {
        "regional_fit_score": total,
        "workforce_component": round(workforce_score * 0.25, 2),
        "infrastructure_component": round(infrastructure_score * 0.20, 2),
        "supplier_component": round(supplier_score * 0.20, 2),
        "energy_component": round(energy_score * 0.15, 2),
        "incentive_component": round(incentive_score * 0.10, 2),
        "logistics_component": round(logistics_score * 0.10, 2),
    }


# ---------------------------------------------------------------------------
# D) Founder Fit Score
# ---------------------------------------------------------------------------

def compute_founder_fit_score(
    expertise_score: float,        # 0-100
    experience_score: float,      # 0-100
    capital_score: float,         # 0-100
    network_score: float,         # 0-100
    location_score: float = 50.0, # 0-100
) -> dict[str, float]:
    """Compute the Founder Fit Score.

    Question: "Who should build this?"

    Formula:
        Founder_Fit =
            expertise_score  * 0.30 +
            experience_score * 0.25 +
            capital_score    * 0.20 +
            network_score    * 0.15 +
            location_score   * 0.10

    Args:
        expertise_score:  Industry knowledge, technical understanding (0-100)
        experience_score: Operations, supply chain, quality, scaling (0-100)
        capital_score:    Personal capital, investor relationships (0-100)
        network_score:    Customer relationships, supplier relationships (0-100)
        location_score:   Geographic proximity to opportunity (0-100)

    Returns:
        dict with founder_fit_score and recommendation (0-100)
    """
    total = (
        expertise_score * 0.30 +
        experience_score * 0.25 +
        capital_score * 0.20 +
        network_score * 0.15 +
        location_score * 0.10
    )
    total = round(min(100.0, max(0.0, total)), 1)

    if total >= 75:
        recommendation = "strong_fit"
    elif total >= 60:
        recommendation = "good_fit"
    elif total >= 40:
        recommendation = "partial_fit"
    else:
        recommendation = "poor_fit"

    return {
        "founder_fit_score": total,
        "expertise_component": round(expertise_score * 0.30, 2),
        "experience_component": round(experience_score * 0.25, 2),
        "capital_component": round(capital_score * 0.20, 2),
        "network_component": round(network_score * 0.15, 2),
        "location_component": round(location_score * 0.10, 2),
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Composite scoring (convenience)
# ---------------------------------------------------------------------------

def compute_all_scores(
    demand_score: float,
    gap_score: float,
    feasibility_score: float,
    timing_score: float,
    competition_score: float,
    # Revival inputs (optional — only for failed company revivals)
    failure_addressed: float | None = None,
    market_change: float | None = None,
    tech_change: float | None = None,
    cost_change: float | None = None,
    policy_change: float | None = None,
    original_failure_severity: float = 1.0,
    years_since_failure: int = 0,
    # Confidence inputs
    data_completeness: float = 0.5,
    source_reliability: float = 0.5,
    evidence_count: int = 0,
) -> dict[str, Any]:
    """Compute all scoring dimensions for a manufacturing opportunity.

    Convenience function that computes opportunity score, revival score (if
    applicable), and confidence in a single call.

    Args:
        (See individual scoring functions above)

    Returns:
        dict with:
            - opportunity: result from compute_opportunity_score()
            - revival: result from compute_revial_score() (if revival inputs provided)
            - confidence: float 0-1
            - model_version: str
    """
    opp_result = compute_opportunity_score(
        demand_score=demand_score,
        gap_score=gap_score,
        feasibility_score=feasibility_score,
        timing_score=timing_score,
        competition_score=competition_score,
    )

    is_revival = all(x is not None for x in [
        failure_addressed, market_change, tech_change, cost_change, policy_change
    ])

    result: dict[str, Any] = {
        "opportunity": opp_result,
        "confidence": compute_confidence(
            data_completeness=data_completeness,
            source_reliability=source_reliability,
            evidence_count=evidence_count,
        ),
        "model_version": MODEL_VERSION,
        "model_score_date": datetime.utcnow().isoformat(),
    }

    if is_revival:
        result["revival"] = compute_revial_score(
            failure_addressed=failure_addressed,
            market_change=market_change,
            tech_change=tech_change,
            cost_change=cost_change,
            policy_change=policy_change,
            original_failure_severity=original_failure_severity,
            years_since_failure=years_since_failure,
        )

    return result


# ---------------------------------------------------------------------------
# Database persistence
# ---------------------------------------------------------------------------

def save_opportunity_scores(
    conn: pymysql.Connection,
    opportunity_data: dict[str, Any],
) -> int | None:
    """Save computed opportunity scores to the manufacturing_opportunities table.

    Args:
        conn: Active MySQL connection (auto-commit False recommended)
        opportunity_data: dict matching manufacturing_opportunities columns

    Returns:
        The inserted row ID, or None on error.
    """
    allowed = {
        "opportunity_type", "title", "description", "sector", "sub_sector",
        "manufacturing_process",
        # Scores
        "opportunity_score", "demand_score", "supply_gap_score", "feasibility_score",
        "timing_score", "competition_score",
        "revival_score", "failure_addressed", "market_change", "tech_change",
        "cost_change", "policy_change",
        # Market
        "total_addressable_market_billion", "service_addressable_market_billion",
        "expected_growth_rate_pct", "addressable_customer_types",
        "estimated_capex_min", "estimated_capex_max",
        "time_to_market_months", "jobs_creation_estimate",
        # Metadata
        "evidence_json", "confidence_score", "confidence_factors_json",
        "model_version", "model_score_date", "status", "priority",
    }

    # Filter to allowed columns
    clean = {k: v for k, v in opportunity_data.items() if k in allowed}
    if "evidence_json" not in clean and "evidence" in opportunity_data:
        clean["evidence_json"] = json.dumps(opportunity_data["evidence"])

    if not clean.get("title"):
        _logger.warning("Cannot save opportunity: missing 'title'")
        return None

    cols = list(clean.keys())
    placeholders = ["%s"] * len(cols)
    values = [clean.get(c) for c in cols]

    sql = f"""
        INSERT INTO manufacturing_opportunities
            ({', '.join(cols)})
        VALUES ({', '.join(placeholders)})
        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            conn.commit()
            return cur.lastrowid
    except Exception as e:
        _logger.error("Failed to save opportunity '%s': %s", clean.get("title"), e)
        return None


# ---------------------------------------------------------------------------
# Unit-test helper
# ---------------------------------------------------------------------------

def _run_tests():
    """Quick smoke tests for the scoring engine."""
    print("=== Opportunity Score Tests ===")
    r = compute_opportunity_score(80, 70, 60, 50, 40)
    print(f"High-opportunity scenario: {r}")

    r2 = compute_opportunity_score(30, 20, 40, 30, 80)
    print(f"Low-opportunity scenario: {r2}")

    print("\n=== Revival Score Tests ===")
    rv = compute_revial_score(80, 70, 60, 50, 40)
    print(f"Strong revival: {rv}")

    rv2 = compute_revial_score(40, 30, 50, 20, 10, original_failure_severity=1.0)
    print(f"Weak revival: {rv2}")

    print("\n=== Regional Fit Score ===")
    rr = compute_regional_fit_score(80, 75, 65, 60, 70, 55)
    print(f"Regional fit: {rr}")

    print("\n=== Founder Fit Score ===")
    ff = compute_founder_fit_score(85, 70, 60, 75, 50)
    print(f" Founder fit: {ff}")

    print("\n=== Confidence Score ===")
    c = compute_confidence(0.8, 0.7, 5)
    print(f"High confidence: {c}")
    c2 = compute_confidence(0.3, 0.4, 1)
    print(f"Low confidence: {c2}")

    print("\n=== All Scores ===")
    all_scores = compute_all_scores(
        demand_score=80, gap_score=70, feasibility_score=65,
        timing_score=55, competition_score=40,
        # Revival inputs
        failure_addressed=75, market_change=70, tech_change=60,
        cost_change=55, policy_change=80,
        original_failure_severity=0.8, years_since_failure=3,
        data_completeness=0.75, source_reliability=0.70, evidence_count=8,
    )
    print(json.dumps(all_scores, indent=2))


if __name__ == "__main__":
    _run_tests()