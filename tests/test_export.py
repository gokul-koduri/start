"""Tests for export_agent and export endpoints."""

from unittest.mock import MagicMock, patch

from api.v2.export import ReportPDF, export_pdf, XPos, YPos  # noqa: E402


class TestPDFExport:
    """Tests for PDF export functionality."""

    def test_report_pdf_instantiation(self):
        """ReportPDF class can be instantiated."""
        pdf = ReportPDF()
        assert pdf is not None
        assert pdf.pages_count == 0

    def test_report_pdf_generates_content(self):
        """PDF with data generates valid content."""
        pdf = ReportPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 10, "Test Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf_bytes = pdf.output()

        assert isinstance(pdf_bytes, (bytes, bytearray))
        assert b"%PDF" in pdf_bytes
        assert b"%%EOF" in pdf_bytes

    def test_report_pdf_with_table(self):
        """PDF with table data."""
        pdf = ReportPDF(orientation="L")
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 10)

        # Header
        col_width = 40
        pdf.cell(col_width, 8, "Name", border=1)
        pdf.cell(col_width, 8, "Score", border=1)
        pdf.cell(col_width, 8, "Status", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Row
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_width, 6, "Test Company", border=1)
        pdf.cell(col_width, 6, "85.5", border=1)
        pdf.cell(col_width, 6, "Active", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf_bytes = pdf.output()
        assert b"%PDF" in pdf_bytes
        assert b"%%EOF" in pdf_bytes
        assert pdf.pages_count == 1

    def test_export_pdf_validates_table(self):
        """export_pdf rejects invalid table names."""
        try:
            export_pdf("invalid_table", 10)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid table" in str(e)

    def test_export_pdf_generates_bytes(self):
        """export_pdf returns bytes when data exists."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.description = [("id",), ("name",), ("score",)]
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Company A", "score": 85.5},
            {"id": 2, "name": "Company B", "score": 72.0},
        ]
        mock_conn.cursor.return_value = mock_cursor

        with patch("api.v2.export.get_connection", return_value=mock_conn):
            with patch("api.v2.export.schema.init_schema"):
                response = export_pdf("failed_startups", 10)

        assert response.media_type == "application/pdf"
        assert b"%PDF" in response.body
        assert b"%%EOF" in response.body
