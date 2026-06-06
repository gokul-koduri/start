"""API v2 Signals router."""

from typing import Optional
from fastapi import APIRouter, Query
from db.connection import get_connection
from db import schema

router = APIRouter(prefix="/v2/signals", tags=["signals"])


@router.get("")
def list_signals(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    signal_type: Optional[str] = Query(None),
    entity_name: Optional[str] = Query(None),
    processed: Optional[int] = Query(None),
):
    """List raw signals (v2 with enhanced filtering)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    query = "SELECT * FROM raw_signals WHERE 1=1"
    params = []

    if signal_type:
        query += " AND signal_type = %s"
        params.append(signal_type)
    if entity_name:
        query += " AND entity_name = %s"
        params.append(entity_name)
    if processed is not None:
        query += " AND processed = %s"
        params.append(processed)

    query += " ORDER BY collected_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    signals = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()
    return {"signals": signals, "limit": limit, "offset": offset}


@router.get("/stats")
def signal_stats():
    """Signal collection statistics (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    stats = {}

    cursor.execute(
        "SELECT signal_type, COUNT(*) as cnt FROM raw_signals GROUP BY signal_type ORDER BY cnt DESC"
    )
    stats["by_type"] = {dict(r)["signal_type"]: dict(r)["cnt"] for r in cursor.fetchall()}

    cursor.execute(
        "SELECT processed, COUNT(*) as cnt FROM raw_signals GROUP BY processed"
    )
    stats["processing_status"] = {str(dict(r)["processed"]): dict(r)["cnt"] for r in cursor.fetchall()}

    cursor.close()
    conn.close()
    return stats
