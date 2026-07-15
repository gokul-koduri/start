"""
Government Manufacturing Intelligence API — Phase v2 MVP.

Endpoints for the Government Dashboard:

GET /government/ohio-manufacturing
    Returns Ohio EV Battery Manufacturing opportunity intelligence.
    Score, rank, and present opportunities relevant to Ohio EDC.

GET /government/opportunities?region=&sector=&decision=
    Query opportunities across regions/sectors.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from db.connection import pooled_connection

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/government", tags=["government"])

MODEL_VERSION = "v2.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decimal_to_float(v: Any) -> Any:
    """Convert Decimal/Float/Numeric values for JSON serialization."""
    import datetime
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime.datetime):
        return v.isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _decimal_to_float(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_decimal_to_float(x) for x in v]
    return v


# ---------------------------------------------------------------------------
# GET /government/ohio-manufacturing
# ---------------------------------------------------------------------------

@router.get("/ohio-manufacturing")
def get_ohio_manufacturing_intelligence() -> JSONResponse:
    """Return Ohio EV Battery Manufacturing opportunity intelligence.

    This is the MVP government dashboard endpoint. Returns scored opportunities
    relevant to Ohio's economic development priorities.

    Query: Single region (Ohio) × manufacturing verticals.

    Returns:
        opportunities: list of scored manufacturing opportunities
        stats: aggregate statistics
        metadata: info about the query (region, timestamp, model version)
    """
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            # Check if manufacturing_opportunities table has data
            cur.execute(
                "SELECT COUNT(*) FROM manufacturing_opportunities WHERE status = 'active'"
            )
            count = cur.fetchone()["COUNT(*)"]

            if count == 0:
                return JSONResponse({
                    "opportunities": [],
                    "stats": {
                        "total_opportunities": 0,
                        "avg_opportunity_score": 0.0,
                        "avg_confidence": 0.0,
                        "total_tam_billion": 0.0,
                        "total_jobs_estimate": 0,
                    },
                    "metadata": {
                        "region": "Ohio",
                        "query_time": datetime.utcnow().isoformat(),
                        "model_version": MODEL_VERSION,
                        "note": "No opportunities in database yet. Run the seeding script to populate.",
                    },
                })

            # Fetch active opportunities ordered by score
            cur.execute("""
                SELECT
                    id,
                    title,
                    opportunity_type,
                    sector,
                    sub_sector,
                    manufacturing_process,
                    -- Scores
                    opportunity_score,
                    demand_score,
                    supply_gap_score,
                    feasibility_score,
                    timing_score,
                    competition_score,
                    -- Market
                    total_addressable_market_billion,
                    service_addressable_market_billion,
                    expected_growth_rate_pct,
                    addressable_customer_types,
                    estimated_capex_min,
                    estimated_capex_max,
                    time_to_market_months,
                    jobs_creation_estimate,
                    -- Metadata
                    confidence_score,
                    description,
                    status,
                    model_score_date
                FROM manufacturing_opportunities
                WHERE status = 'active'
                ORDER BY opportunity_score DESC, confidence_score DESC
                LIMIT 50
            """)
            rows = cur.fetchall()

    # Process and serialize
    opportunities = []
    total_tam = 0.0
    total_jobs = 0
    score_sum = 0.0
    conf_sum = 0.0

    for row in rows:
        opp = _decimal_to_float(dict(row))

        # Parse customer types from JSON if stored as string
        cust_types = opp.get("addressable_customer_types") or []
        if isinstance(cust_types, str):
            try:
                cust_types = json.loads(cust_types)
            except Exception:
                cust_types = [cust_types] if cust_types else []
        opp["addressable_customer_types"] = cust_types

        # Compute decision label from score
        score = opp.get("opportunity_score", 0)
        if score >= 75:
            decision = "strong_recommendation"
        elif score >= 60:
            decision = "conditional_recommendation"
        elif score >= 45:
            decision = "requires_validation"
        else:
            decision = "not_recommended"

        opp["decision"] = decision

        # Confidence label
        conf = opp.get("confidence_score", 0)
        if conf >= 0.75:
            conf_label = "high"
        elif conf >= 0.5:
            conf_label = "medium"
        else:
            conf_label = "low"
        opp["confidence_label"] = conf_label

        opportunities.append(opp)
        total_tam += float(opp.get("total_addressable_market_billion") or 0)
        total_jobs += int(opp.get("jobs_creation_estimate") or 0)
        score_sum += score
        conf_sum += conf

    n = len(opportunities)
    return JSONResponse({
        "opportunities": opportunities,
        "stats": {
            "total_opportunities": n,
            "avg_opportunity_score": round(score_sum / n, 1) if n else 0.0,
            "avg_confidence": round(conf_sum / n, 2) if n else 0.0,
            "total_tam_billion": round(total_tam, 1),
            "total_jobs_estimate": total_jobs,
        },
        "metadata": {
            "region": "Ohio",
            "query_time": datetime.utcnow().isoformat(),
            "model_version": MODEL_VERSION,
            "confidence_note": "CAPEX estimates require supplier validation. Scores are directional.",
        },
    })


# ---------------------------------------------------------------------------
# GET /government/opportunities
# ---------------------------------------------------------------------------

@router.get("/opportunities")
def list_government_opportunities(
    region: str = Query(None, description="Filter by region"),
    sector: str = Query(None, description="Filter by sector"),
    decision: str = Query(None, description="Filter by decision (strong_recommendation, etc.)"),
    min_score: float = Query(0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    """Query manufacturing opportunities with filters.

    Supports government decision-makers by allowing filtered lookups
    across regions and sectors.
    """
    conditions = ["status = 'active'"]
    params: list[Any] = []

    if region:
        conditions.append("region = %s")
        params.append(region)
    if sector:
        conditions.append("(sector = %s OR sub_sector = %s)")
        params.extend([sector, sector])
    if min_score is not None:
        conditions.append("opportunity_score >= %s")
        params.append(min_score)

    where = " AND ".join(conditions) if conditions else "1=1"

    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    id, title, opportunity_type, sector, sub_sector,
                    opportunity_score, demand_score, supply_gap_score,
                    feasibility_score, timing_score, competition_score,
                    confidence_score, description,
                    total_addressable_market_billion, estimated_capex_min,
                    estimated_capex_max, time_to_market_months,
                    jobs_creation_estimate, status, created_at
                FROM manufacturing_opportunities
                WHERE {where}
                ORDER BY opportunity_score DESC
                LIMIT %s OFFSET %s
            """, [*params, limit, offset])
            rows = cur.fetchall()

            cur.execute(
                f"SELECT COUNT(*) FROM manufacturing_opportunities WHERE {where}",
                params
            )
            total = cur.fetchone()["COUNT(*)"]

    opportunities = []
    for row in rows:
        opp = _decimal_to_float(dict(row))
        score = opp.get("opportunity_score", 0)
        opp["decision"] = (
            "strong_recommendation" if score >= 75
            else "conditional_recommendation" if score >= 60
            else "requires_validation" if score >= 45
            else "not_recommended"
        )
        opportunities.append(opp)

    return JSONResponse({
        "opportunities": opportunities,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


# ---------------------------------------------------------------------------
# GET /government/opportunities/{id}
# ---------------------------------------------------------------------------

@router.get("/opportunities/{opp_id}")
def get_opportunity_detail(opp_id: int) -> JSONResponse:
    """Get full detail for a specific manufacturing opportunity."""
    with pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM manufacturing_opportunities WHERE id = %s
            """, (opp_id,))
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opp = _decimal_to_float(dict(row))
    score = opp.get("opportunity_score", 0)
    opp["decision"] = (
        "strong_recommendation" if score >= 75
        else "conditional_recommendation" if score >= 60
        else "requires_validation" if score >= 45
        else "not_recommended"
    )
    return JSONResponse(opp)