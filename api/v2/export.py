"""API v2 Export router."""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from db.connection import get_connection
from db import schema
import csv
import io

router = APIRouter(prefix="/v2/export", tags=["export"])


@router.get("/csv")
def export_csv(
    table: str = Query("failed_startups"),
    limit: int = Query(1000, ge=1, le=10000),
):
    """Export table data as CSV (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Validate table name to prevent SQL injection
    valid_tables = [
        "failed_startups",
        "news_articles",
        "opportunity_scores",
        "raw_signals",
        "funding_events",
        "patent_filings",
    ]
    if table not in valid_tables:
        cursor.close()
        conn.close()
        return {"error": f"Invalid table. Valid tables: {', '.join(valid_tables)}"}

    cursor.execute(f"SELECT * FROM {table} LIMIT %s", (limit,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)

    # Stream response
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table}_export.csv"},
    )


@router.get("/json")
def export_json(
    table: str = Query("failed_startups"),
    limit: int = Query(1000, ge=1, le=10000),
):
    """Export table data as JSON (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Validate table name
    valid_tables = [
        "failed_startups",
        "news_articles",
        "opportunity_scores",
        "raw_signals",
        "funding_events",
        "patent_filings",
    ]
    if table not in valid_tables:
        cursor.close()
        conn.close()
        return {"error": f"Invalid table. Valid tables: {', '.join(valid_tables)}"}

    cursor.execute(f"SELECT * FROM {table} LIMIT %s", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {"table": table, "count": len(rows), "data": rows}
