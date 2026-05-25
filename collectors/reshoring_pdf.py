"""Reshoring Initiative PDF parser for reshoring/job statistics."""

import sqlite3
import logging
import re
import hashlib
from pathlib import Path

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

# Regex patterns for extracting data from Reshoring Initiative PDFs
_JOB_COUNT_PATTERNS = [
    re.compile(r"(\d{1,3}(?:,\d{3})+)\s+jobs?\s+(?:announced|created|brought)", re.IGNORECASE),
    re.compile(r"(\d{1,3}(?:,\d{3})+)\s+jobs?\s+from\s+(?:reshoring|FDI)", re.IGNORECASE),
    re.compile(r"(\d{1,3}(?:,\d{3})+)\s+(?:total|net)\s+jobs?", re.IGNORECASE),
    re.compile(r"announced\s+(\d{1,3}(?:,\d{3})+)\s+jobs?", re.IGNORECASE),
]

_SUCCESS_RATE_PATTERNS = [
    re.compile(r"(\d+)%\s+(?:success|completion|fulfillment)", re.IGNORECASE),
    re.compile(r"success\s+rate\s+of\s+(\d+)%", re.IGNORECASE),
]


class ReshoringPDFCollector(BaseCollector):
    """Downloads and parses Reshoring Initiative annual PDF reports."""

    @property
    def name(self) -> str:
        return "reshoring_pdf"

    def collect(self, conn: sqlite3.Connection) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        pdf_config = self.config.get("pdf", {}).get("reshoring_initiative", {})
        known_pdfs = pdf_config.get("known_pdfs", [])
        download_dir = pdf_config.get("pdf_download_dir", "data/pdfs")

        # Ensure download directory exists
        dl_path = Path(download_dir)
        dl_path.mkdir(parents=True, exist_ok=True)

        session = get_http_session()

        for pdf_info in known_pdfs:
            pdf_url = pdf_info["url"]
            report_year = pdf_info["report_year"]
            data_year = pdf_info["data_year"]

            _logger.info("Processing Reshoring Initiative PDF: year=%d, url=%s", data_year, pdf_url)

            # Download PDF
            local_path = dl_path / f"reshoring_{data_year}.pdf"
            try:
                if not self._download_pdf(session, pdf_url, local_path):
                    result.errors.append(f"Failed to download {pdf_url}")
                    continue
            except Exception as e:
                result.errors.append(f"Download error for {pdf_url}: {e}")
                continue

            # Parse PDF
            text = self._extract_text(local_path)
            if not text:
                result.errors.append(f"No text extracted from {local_path}")
                continue

            _logger.info("Extracted %d characters from PDF", len(text))

            # Extract data
            records = self._extract_data(text, data_year, pdf_url, report_year)

            # Insert into database
            for rec in records:
                if rec["type"] == "summary":
                    if not self.dry_run:
                        conn.execute(
                            """INSERT OR REPLACE INTO reshoring_summary_stats
                               (stat_year, total_jobs, success_rate_pct, key_policy, headline, source, collected_at)
                               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                            (rec["data_year"], rec.get("total_jobs"),
                             rec.get("success_rate"), rec.get("key_policy"),
                             rec.get("headline"), rec.get("source")),
                        )
                elif rec["type"] == "industry":
                    if not self.dry_run:
                        conn.execute(
                            """INSERT INTO reshoring_data
                               (report_year, data_year, industry, jobs_created, jobs_announced,
                                success_rate_pct, cost_reduction_pct, notes,
                                source_report, source_url, collected_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                            (report_year, rec["data_year"], rec.get("industry"),
                             rec.get("jobs_created"), rec.get("jobs_announced"),
                             rec.get("success_rate"), rec.get("cost_reduction"),
                             rec.get("notes"), rec.get("source"), pdf_url),
                        )
                result.records_collected += 1
                result.records_inserted += 1

            conn.commit()

        result.status = "partial" if result.errors else "success"
        return result

    def _download_pdf(self, session, url: str, local_path: Path) -> bool:
        """Download a PDF if it doesn't exist or has changed."""
        # Check if file exists
        if local_path.exists():
            _logger.info("PDF already exists: %s", local_path)
            return True

        _logger.info("Downloading PDF: %s", url)
        try:
            resp = session.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            _logger.info("Downloaded %d bytes to %s", local_path.stat().st_size, local_path)
            return True
        except Exception as e:
            _logger.error("Download failed: %s", e)
            return False

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract text from a PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            _logger.error("PyMuPDF (fitz) not installed. Run: pip install PyMuPDF")
            return ""

        text_parts = []
        try:
            doc = fitz.open(str(pdf_path))
            for page in doc:
                text_parts.append(page.get_text("text"))
            doc.close()
        except Exception as e:
            _logger.error("PDF extraction failed: %s", e)
            return ""

        return "\n".join(text_parts)

    def _extract_data(self, text: str, data_year: int, source_url: str, report_year: int) -> list[dict]:
        """Extract structured data from PDF text using multiple strategies."""
        records = []
        source_report = f"Reshoring Initiative {report_year} Annual Report"

        # Strategy 1: Find total job counts
        total_jobs = None
        for pattern in _JOB_COUNT_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                # Take the largest job count found
                counts = [int(m.replace(",", "")) for m in matches]
                total_jobs = max(counts)
                break

        # Strategy 2: Find success rate
        success_rate = None
        for pattern in _SUCCESS_RATE_PATTERNS:
            match = pattern.search(text)
            if match:
                success_rate = float(match.group(1))
                break

        # Strategy 3: Look for industry-specific data
        # Common reshoring industries to search for
        industries = [
            "semiconductor", "battery", "steel", "metal", "auto", "automotive",
            "electronics", "solar", "textile", "pharmaceutical", "chemical",
            "plastic", "rubber", "food", "machinery", "appliance",
            "aerospace", "defense", "medical device",
        ]

        for industry in industries:
            # Look for job counts near industry mentions
            industry_pattern = re.compile(
                rf"{industry}[^.]*?(\d{{1,3}}(?:,\d{{3}})+)\s*jobs?",
                re.IGNORECASE,
            )
            match = industry_pattern.search(text)
            if match:
                industry_jobs = int(match.group(1).replace(",", ""))
                records.append({
                    "type": "industry",
                    "data_year": data_year,
                    "industry": industry.title(),
                    "jobs_created": industry_jobs,
                    "source": source_report,
                })

        # Strategy 4: Look for industry tables
        # Try to find sections that list industries with numbers
        table_pattern = re.compile(
            r"((?:semiconductor|battery|steel|auto|electronics|solar|textile|chemical)[^\n]{0,100}"
            r"(?:\d{1,3}(?:,\d{3})+)[^\n]{0,100})",
            re.IGNORECASE,
        )
        for match in table_pattern.finditer(text):
            _logger.debug("Table-like match: %s", match.group(1)[:100])

        # Build summary record
        headline_parts = []
        if total_jobs:
            headline_parts.append(f"{total_jobs:,} jobs announced")
        if success_rate:
            headline_parts.append(f"{int(success_rate)}% success rate")

        key_policy = None
        if "CHIPS" in text:
            key_policy = "CHIPS Act ($52B)"
        if "IRA" in text or "Inflation Reduction" in text:
            if key_policy:
                key_policy += "; IRA ($369B)"
            else:
                key_policy = "IRA ($369B)"

        records.append({
            "type": "summary",
            "data_year": data_year,
            "total_jobs": total_jobs,
            "success_rate": success_rate,
            "key_policy": key_policy,
            "headline": ". ".join(headline_parts) if headline_parts else None,
            "source": source_report,
        })

        # Mark low-confidence if we couldn't extract much
        if total_jobs is None and success_rate is None and len(records) <= 1:
            _logger.warning("Low confidence extraction from reshoring PDF for year %d", data_year)

        return records
