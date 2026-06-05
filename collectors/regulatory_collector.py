"""Regulatory collector — fetches SEC filings from EDGAR RSS feeds.

Data source: SEC EDGAR RSS feeds (no auth required).
Rate limit: No strict limit — uses polite delay between requests.

This collector tracks S-1 (IPO), 8-K (current reports), and SC 13D (beneficial ownership)
filings to identify major corporate events, funding signals, and market movements.
"""

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_BASE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

# SEC EDGAR RSS XML namespaces
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "sec": "http://www.sec.gov/Archives/edgar",
}


class RegulatoryCollector(BaseCollector):
    """Collects SEC regulatory filings from EDGAR RSS feeds.

    Fetches S-1, 8-K, and SC 13D filings for configurable companies and terms.
    Parses Atom XML responses and stores filing metadata.

    Config options:
        regulatory.base_url: EDGAR base URL
        regulatory.search_companies: list of company search terms
        regulatory.filing_types: list of filing type filters (S-1, 8-K, SC 13D)
        regulatory.max_results_per_query: results per query (default: 40)
        regulatory.min_delay_seconds: delay between API calls (default: 3)
        regulatory.user_agent: User-Agent string for requests
    """

    @property
    def name(self) -> str:
        return "regulatory"

    def _build_url(self, company: str = "", filing_types: list[str] | None = None) -> str:
        """Build EDGAR browse URL for a company or general filing search."""
        params = {
            "action": "getcompany",
            "owner": "include",
            "count": 40,
            "output": "atom",
        }

        if company:
            params["company"] = company

        if filing_types:
            # EDGAR expects comma-separated filing types
            params["type"] = ",".join(filing_types)

        # Build query string
        query_parts = []
        for key, value in params.items():
            if value:
                query_parts.append(f"{key}={quote(str(value))}")

        return f"{_BASE_URL}?{'&'.join(query_parts)}"

    def _fetch_filings(self, session, url: str) -> list[dict]:
        """Fetch filings from SEC EDGAR RSS feed and parse Atom XML response."""
        try:
            headers = {
                "User-Agent": self.config.get("regulatory", {}).get("user_agent",
                    "StartupResearchBot/1.0 (educational research project)")
            }
            resp = session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            _logger.warning("SEC EDGAR request failed: %s — %s", url, e)
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as e:
            _logger.warning("SEC EDGAR XML parse failed: %s", e)
            return []

        entries = []
        for entry in root.findall("atom:entry", _NS):
            filing = self._parse_entry(entry)
            if filing:
                entries.append(filing)

        return entries

    def _parse_entry(self, entry: ET.Element) -> dict | None:
        """Extract filing metadata from an Atom entry element."""
        # Filing ID from <id> tag (e.g., https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=S-1)
        filing_url = entry.findtext("atom:id", default="", namespaces=_NS)

        # Extract filing accession number from URL or summary
        filing_id = ""
        for link in entry.findall("atom:link", _NS):
            href = link.get("href", "")
            if "accession_number" in href:
                # Extract accession number from URL
                parts = href.split("accession_number=")
                if len(parts) > 1:
                    filing_id = parts[1].split("&")[0]
                    break

        # If not found in link, try to extract from title or summary
        if not filing_id:
            title = entry.findtext("atom:title", default="", namespaces=_NS)
            if "ACC NO:" in title:
                filing_id = title.split("ACC NO:")[-1].strip().split()[0]

        if not filing_id:
            # Use URL hash as fallback ID
            filing_id = filing_url.split("CIK=")[-1].split("&")[0] if "CIK=" in filing_url else ""

        # Title contains filing type and company info
        title = entry.findtext("atom:title", default="", namespaces=_NS).strip()
        title = " ".join(title.split())  # Collapse whitespace

        # Extract filing type from title (e.g., "S-1", "8-K", "SC 13D")
        filing_type = ""
        for ft in ["SC 13D", "S-1", "8-K"]:
            if ft in title:
                filing_type = ft
                break

        # Summary contains company name and filing details
        summary = entry.findtext("atom:summary", default="", namespaces=_NS).strip()
        summary = " ".join(summary.split())

        # Extract company name from summary (usually formatted as "Company Name (CIK: ########)")
        company_name = ""
        if "(CIK:" in summary:
            company_name = summary.split("(CIK:")[0].strip()
        elif summary:
            # Fallback: use first line of summary
            company_name = summary.split("\n")[0].strip()

        # Filing date from <updated> tag
        filed_date_str = entry.findtext("atom:updated", default="", namespaces=_NS)
        filed_date = self._parse_date(filed_date_str)

        # Link to filing document
        link = ""
        for link_elem in entry.findall("atom:link", _NS):
            if link_elem.get("rel") == "alternate":
                link = link_elem.get("href", "")
                break

        return {
            "filing_id": filing_id,
            "filing_type": filing_type,
            "company_name": company_name,
            "summary": summary,
            "filed_date": filed_date,
            "link": link,
        }

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse ISO date string to datetime object."""
        if not date_str:
            return None
        try:
            # SEC dates like "2024-01-15T12:34:56-05:00"
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None

    def _compute_score(self, filing: dict) -> float:
        """Compute signal strength (0-100).

        Factors:
          - S-1 filing (IPO signal): +30
          - 8-K filing (material event): +20
          - SC 13D filing (activist investor): +25
          - Recent filing (< 7 days): +20
          - Recent filing (< 30 days): +10
        """
        score = 0.0

        # Filing type weight
        filing_type = filing.get("filing_type", "")
        if filing_type == "S-1":
            score += 30  # IPO signal
        elif filing_type == "SC 13D":
            score += 25  # Activist investor / major ownership change
        elif filing_type == "8-K":
            score += 20  # Material corporate event

        # Recency bonus
        filed_date = filing.get("filed_date")
        if filed_date:
            if isinstance(filed_date, str):
                try:
                    filed_date = datetime.fromisoformat(filed_date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    filed_date = None

            if filed_date and isinstance(filed_date, datetime):
                if filed_date.tzinfo is None:
                    filed_date = filed_date.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                age_days = (now - filed_date).days

                if age_days < 7:
                    score += 20
                elif age_days < 30:
                    score += 10

        return min(score, 100.0)

    def _insert_filing(self, cursor, filing: dict, result: CollectionResult) -> None:
        """Insert filing into regulatory_filings and raw_signals."""
        filing_id = filing["filing_id"]
        filing_type = filing["filing_type"]
        company_name = filing["company_name"]
        summary = filing["summary"]
        filed_date = filing["filed_date"]
        link = filing["link"]

        raw_score = self._compute_score(filing)

        # Convert datetime to ISO string for storage
        filed_date_str = None
        if filed_date:
            if isinstance(filed_date, datetime):
                filed_date_str = filed_date.isoformat()
            else:
                filed_date_str = filed_date

        # Insert into regulatory_filings
        cursor.execute(
            """INSERT INTO regulatory_filings
               (filing_id, filing_type, company_name, summary, filed_date, link, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 filing_type = VALUES(filing_type),
                 company_name = VALUES(company_name),
                 summary = VALUES(summary),
                 filed_date = VALUES(filed_date),
                 link = VALUES(link),
                 collected_at = VALUES(collected_at)""",
            (
                filing_id,
                filing_type,
                company_name,
                summary or None,
                filed_date_str,
                link or None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Insert into raw_signals
        cursor.execute(
            """INSERT IGNORE INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at, collected_at, processed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
            (
                "sec_filing",
                "sec_edgar",
                link,
                f"{filing_type} - {company_name}",
                summary[:500] if summary else "",
                company_name,
                filed_date_str,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "sec_filing",
            title=f"{filing_type} - {company_name}",
            entity_name=company_name,
            source_url=link,
            body_text=summary[:300] if summary else "",
            raw_score=raw_score,
            filing_type=filing_type,
            filing_id=filing_id,
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("regulatory", {})

        if self.dry_run:
            result.status = "success"
            return result

        search_companies = config.get("search_companies", ["AI startup", "tech company"])
        filing_types = config.get("filing_types", ["S-1", "8-K", "SC 13D"])
        base_url = config.get("base_url", _BASE_URL)
        max_results = config.get("max_results_per_query", 40)
        min_delay = config.get("min_delay_seconds", 3)

        session = get_http_session(timeout=30)
        session.headers["Accept"] = "application/xml"

        cursor = conn.cursor()

        # Fetch general filings (no company filter)
        general_url = self._build_url(company="", filing_types=filing_types)
        filings = self._fetch_filings(session, general_url)

        for filing in filings[:max_results]:
            try:
                self._insert_filing(cursor, filing, result)
            except Exception as e:
                result.errors.append(f"Error inserting filing {filing.get('filing_id', '?')}: {e}")

        _logger.info(
            "RegulatoryCollector: general feed → %d filings",
            len(filings[:max_results]),
        )

        # Fetch company-specific filings
        for company in search_companies:
            company_url = self._build_url(company=company, filing_types=filing_types)
            company_filings = self._fetch_filings(session, company_url)

            for filing in company_filings[:max_results]:
                try:
                    self._insert_filing(cursor, filing, result)
                except Exception as e:
                    result.errors.append(f"Error inserting filing {filing.get('filing_id', '?')}: {e}")

            time.sleep(min_delay)  # Polite delay between requests

            _logger.info(
                "RegulatoryCollector: company '%s' → %d filings",
                company, len(company_filings[:max_results]),
            )

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
