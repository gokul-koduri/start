"""API v2 Export router."""

from datetime import datetime
from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse
from fpdf import FPDF, XPos, YPos
from db.connection import get_connection
from db import schema
import csv
import io

try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False

router = APIRouter(prefix="/v2/export", tags=["export"])


def export_watchlist_csv(watchlist_id: int) -> Response:
    """Export watchlist items as CSV.

    This is a standalone export function callable from tests or other modules.
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Get watchlist name
    cursor.execute(
        "SELECT name FROM watchlists WHERE id = %s AND is_active = 1",
        (watchlist_id,),
    )
    watchlist = cursor.fetchone()

    if not watchlist:
        cursor.close()
        conn.close()
        raise ValueError(f"Watchlist {watchlist_id} not found")

    # Get watchlist items
    cursor.execute(
        """SELECT wli.entity_name, wli.entity_type, wli.notes, wli.added_at,
                  os.composite_score, os.trend_direction
           FROM watchlist_items wli
           LEFT JOIN opportunity_scores os ON os.entity_name = wli.entity_name
           WHERE wli.watchlist_id = %s
           ORDER BY wli.added_at DESC""",
        (watchlist_id,),
    )
    rows = cursor.fetchall()
    columns = (
        [desc[0] for desc in cursor.description]
        if cursor.description
        else [
            "entity_name",
            "entity_type",
            "notes",
            "added_at",
            "composite_score",
            "trend_direction",
        ]
    )

    cursor.close()
    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(
            [row.get(col) if row.get(col) is not None else "" for col in columns]
        )

    output.seek(0)
    filename = f"watchlist_{watchlist_id}_export.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class ReportPDF(FPDF):
    """Custom PDF class for report exports."""

    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(
            0,
            10,
            "Startup Research Report",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def export_pdf(table_name: str, limit: int = 100) -> Response:
    """Export table data as a formatted PDF report.

    Args:
        table_name: Name of the table to export
        limit: Maximum number of rows to include

    Returns:
        PDF response with formatted table
    """
    valid_tables = [
        "failed_startups",
        "news_articles",
        "opportunity_scores",
        "raw_signals",
        "funding_events",
        "patent_filings",
    ]
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table. Valid tables: {', '.join(valid_tables)}")

    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []

    cursor.close()
    conn.close()

    # Create PDF
    pdf = ReportPDF(orientation="L")  # Landscape for better table width
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title and metadata
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0, 10, f"Export: {table_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C"
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        6,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    pdf.cell(
        0,
        6,
        f"Total records: {len(rows)}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    pdf.ln(10)

    if not columns:
        pdf.cell(
            0, 10, "No data available", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C"
        )
    else:
        # Table header
        pdf.set_fill_color(33, 37, 41)  # Dark gray
        pdf.set_text_color(255, 255, 255)  # White
        pdf.set_font("Helvetica", "B", 9)

        col_width = (pdf.w - 20) / min(len(columns), 8)  # Max 8 visible columns
        for col in columns[:8]:  # Limit to first 8 columns for readability
            pdf.cell(col_width, 8, str(col)[:20], border=1, fill=True, align="C")
        pdf.ln()

        # Table rows
        pdf.set_text_color(0, 0, 0)  # Black
        pdf.set_font("Helvetica", "", 8)
        fill = False

        for i, row in enumerate(rows[:50]):  # Limit display to 50 rows per page section
            bg_color = (245, 245, 245) if fill else (255, 255, 255)
            pdf.set_fill_color(*bg_color)
            fill = not fill

            for col in columns[:8]:
                value = row.get(col)
                if value is None:
                    cell_value = "-"
                elif isinstance(value, datetime):
                    cell_value = value.strftime("%Y-%m-%d")
                elif isinstance(value, float):
                    cell_value = f"{value:.2f}"
                elif isinstance(value, int):
                    cell_value = str(value)
                else:
                    cell_value = str(value)[:25]
                pdf.cell(col_width, 6, cell_value, border=1, fill=True, align="L")
            pdf.ln()

        if len(rows) > 50:
            pdf.ln(5)
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(
                0,
                6,
                f"... and {len(rows) - 50} more records",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
                align="C",
            )

    # Save to bytes (fpdf.output() returns bytearray, convert to bytes)
    pdf_bytes = bytes(pdf.output())

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={table_name}_export.pdf"
        },
    )


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


@router.get("/pdf")
def export_pdf_endpoint(
    table: str = Query("failed_startups"),
    limit: int = Query(100, ge=1, le=500),
):
    """Export table data as formatted PDF report."""
    return export_pdf(table, limit)


@router.get("/parquet")
def export_parquet_endpoint(
    table: str = Query("failed_startups"),
    limit: int = Query(1000, ge=1, le=10000),
):
    """Export table data as Parquet file for data pipelines.

    Parquet is a columnar format that's efficient for analytics workloads.
    Requires pyarrow to be installed.
    """
    if not PARQUET_AVAILABLE:
        return {
            "error": "Parquet export requires pyarrow. Install with: pip install pyarrow"
        }

    valid_tables = [
        "failed_startups",
        "news_articles",
        "opportunity_scores",
        "raw_signals",
        "funding_events",
        "patent_filings",
    ]
    if table not in valid_tables:
        return {"error": f"Invalid table. Valid tables: {', '.join(valid_tables)}"}

    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table} LIMIT %s", (limit,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []

    cursor.close()
    conn.close()

    if not rows:
        return {"error": "No data to export", "table_name": table}

    # Convert to PyArrow table
    data = {col: [] for col in columns}
    for row in rows:
        for col in columns:
            value = row.get(col)
            # Convert datetime to string for Parquet compatibility
            if isinstance(value, datetime):
                value = value.isoformat()
            data[col].append(value)

    pyarrow_data = {col: pa.array(data[col]) for col in columns}
    pa_table = pa.table(pyarrow_data)

    # Convert to Parquet bytes
    parquet_buffer = io.BytesIO()
    pq.write_table(pa_table, parquet_buffer, compression="snappy")
    parquet_bytes = parquet_buffer.getvalue()

    return Response(
        content=parquet_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={table}_export.parquet"},
    )
