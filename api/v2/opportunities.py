"""API v2 Opportunities router."""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from db.connection import get_connection
from db import schema
import json

router = APIRouter(prefix="/v2/opportunities", tags=["opportunities"])


@router.get("")
def list_opportunities(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_score: float = Query(0),
    trend: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
):
    """List scored opportunities (v2 with pagination)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    query = "SELECT * FROM opportunity_scores WHERE composite_score >= %s"
    params = [min_score]

    if trend:
        query += " AND trend_direction = %s"
        params.append(trend)
    if entity_type:
        query += " AND entity_type = %s"
        params.append(entity_type)

    query += " ORDER BY composite_score DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    opportunities = []
    for row in rows:
        opp = dict(row)
        if opp.get("attribution_json"):
            try:
                opp["attribution"] = json.loads(opp["attribution_json"])
            except (json.JSONDecodeError, TypeError):
                opp["attribution"] = []
        opportunities.append(opp)

    cursor.close()
    conn.close()

    return {"opportunities": opportunities, "limit": limit, "offset": offset}


@router.get("/{entity_name}")
def get_opportunity(entity_name: str):
    """Get detailed opportunity by entity name (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM opportunity_scores WHERE entity_name = %s",
        (entity_name,),
    )
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found")

    opp = dict(row)
    if opp.get("signal_weights_json"):
        try:
            opp["signal_weights"] = json.loads(opp["signal_weights_json"])
        except (json.JSONDecodeError, TypeError):
            opp["signal_weights"] = []

    cursor.close()
    conn.close()
    return opp
