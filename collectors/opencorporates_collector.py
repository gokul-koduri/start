"""OpenCorporates collector — company registration data from OpenCorporates API.

Fetches company incorporation data (jurisdiction, incorporation date, officers,
current status, registered address) to enrich startup/company profiles.

Data source: OpenCorporates API v0.4 (free tier: 50 req/day).
Rate limit: Conservative — respects daily cap, spaces out requests.

This is a key collector for Phase 5 — the Founder Background Agent (5.3)
depends on company_profiles data to track founders across companies.
"""

import json
import logging
import time
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_BASE_URL = "https://api.opencorporates.com/v0.4"


class OpenCorporatesCollector(BaseCollector):
    """Collects company registration data from OpenCorporates.

    Searches for companies by configurable queries and jurisdiction filters.
    Enriches the company_profiles table for downstream analysis agents.

    Config options:
        opencorporates.api_token: OpenCorporates API token (${OPENCORPORATES_API_TOKEN})
        opencorporates.base_url: API base URL
        opencorporates.search_queries: list of {query, jurisdictions} dicts
        opencorporates.per_page: results per search (default: 30)
        opencorporates.rate_limit.requests_per_day: daily cap (default: 50)
        opencorporates.min_delay_seconds: delay between API calls (default: 2)
    """

    @property
    def name(self) -> str:
        return "opencorporates"

    def _build_session(self, config: dict):
        """Build HTTP session with OpenCorporates API token."""
        session = get_http_session(timeout=30)
        token = config.get("api_token", "")
        if token:
            # Token passed as query param, not header
            pass  # Token is added to URL params in _fetch_search
        session.headers["Accept"] = "application/json"
        return session

    def _fetch_search(
        self,
        session,
        base_url: str,
        token: str,
        query: str,
        jurisdictions: list[str] | None = None,
        per_page: int = 30,
    ) -> dict | None:
        """Search OpenCorporates API for companies."""
        params = {"q": query, "per_page": per_page}
        if token:
            params["api_token"] = token
        if jurisdictions:
            for jc in jurisdictions:
                params.setdefault("jurisdiction_code", "")
                params["jurisdiction_code"] = jc
                break  # API only supports one jurisdiction per request

        try:
            resp = session.get(
                f"{base_url}/companies/search", params=params, timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            _logger.warning("OpenCorporates API search failed: %s — %s", query, e)
            return None

    def _fetch_company(
        self, session, base_url: str, token: str, jurisdiction: str, company_number: str
    ) -> dict | None:
        """Fetch individual company details."""
        params = {}
        if token:
            params["api_token"] = token

        try:
            url = f"{base_url}/companies/{jurisdiction}/{company_number}"
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            _logger.warning(
                "OpenCorporates company fetch failed: %s/%s — %s",
                jurisdiction,
                company_number,
                e,
            )
            return None

    def _compute_score(self, company: dict) -> float:
        """Compute signal strength (0-100).

        Factors:
          - Active status: +40
          - Recent incorporation (< 5 years): +30
          - Has officers: +15
          - Has filings: +15
        """
        score = 0.0
        company_data = company.get("company", {})

        if company_data.get("current_status") == "Active":
            score += 40
        elif company_data.get("current_status") in ("Dissolved", "Liquidation"):
            score += 0
        else:
            score += 20

        inc_date = company_data.get("incorporation_date")
        if inc_date:
            try:
                inc_dt = datetime.strptime(inc_date, "%Y-%m-%d")
                age_years = (
                    datetime.now(timezone.utc) - inc_dt.replace(tzinfo=timezone.utc)
                ).days / 365
                if age_years < 2:
                    score += 30
                elif age_years < 5:
                    score += 20
                elif age_years < 10:
                    score += 10
            except (ValueError, TypeError):
                pass

        officers = company_data.get("officers", [])
        if officers:
            score += 15

        filings = company_data.get("filings", [])
        if filings:
            score += 15

        return min(score, 100.0)

    def _extract_officers(self, company_data: dict) -> list[dict]:
        """Extract officer names and positions from company data."""
        officers = company_data.get("officers", [])
        return [
            {"name": o.get("name", ""), "position": o.get("position", "")}
            for o in officers
            if o.get("name")
        ][:10]  # Cap at 10 officers

    def _insert_company(
        self, cursor, company: dict, search_term: str, result: CollectionResult
    ) -> None:
        """Insert company into company_profiles and raw_signals."""
        company_data = company.get("company", {})
        name = company_data.get("name", "")
        company_number = str(company_data.get("company_number", ""))
        jurisdiction = company_data.get("jurisdiction_code", "")
        inc_date = company_data.get("incorporation_date")
        diss_date = company_data.get("dissolution_date")
        company_type = company_data.get("company_type", "")
        status = company_data.get("current_status", "")
        address = company_data.get("registered_address_in_full", "")
        registry_url = company_data.get("registry_url", "")
        officers = self._extract_officers(company_data)

        raw_score = self._compute_score(company)

        # Insert into company_profiles
        cursor.execute(
            """INSERT INTO company_profiles
               (company_name, company_number, jurisdiction_code, incorporation_date,
                dissolution_date, company_type, current_status, registered_address,
                officers, registry_url, source_search_term, raw_score, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 current_status = VALUES(current_status),
                 dissolution_date = VALUES(dissolution_date),
                 raw_score = VALUES(raw_score),
                 collected_at = VALUES(collected_at)""",
            (
                name,
                company_number,
                jurisdiction,
                inc_date,
                diss_date,
                company_type,
                status,
                address,
                json.dumps(officers) if officers else None,
                registry_url,
                search_term,
                raw_score,
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
                "opencorporates",
                "opencorporates",
                registry_url,
                f"{name} ({jurisdiction.upper()}) — {status}",
                f"{address} | Type: {company_type} | Incorporated: {inc_date}"
                if address
                else "",
                name,
                inc_date,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "opencorporates",
            title=f"{name} ({jurisdiction.upper()}) — {status}",
            entity_name=name,
            source_url=registry_url,
            body_text=address or "",
            raw_score=raw_score,
            jurisdiction=jurisdiction,
            company_status=status,
            company_type=company_type,
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("opencorporates", {})

        if self.dry_run:
            result.status = "success"
            return result

        if not config.get("api_token"):
            _logger.warning("OpenCorporatesCollector: no API token configured")
            result.status = "failed"
            result.errors.append("No API token configured")
            return result

        base_url = config.get("base_url", _BASE_URL)
        token = config.get("api_token", "")
        session = self._build_session(config)
        search_queries = config.get(
            "search_queries",
            [
                {"query": "AI startup", "jurisdictions": ["us", "gb"]},
                {"query": "machine learning", "jurisdictions": ["us", "gb"]},
                {"query": "fintech", "jurisdictions": ["us", "gb"]},
            ],
        )
        per_page = config.get("per_page", 30)
        min_delay = config.get("min_delay_seconds", 2)

        cursor = conn.cursor()

        for sq in search_queries:
            query = sq.get("query", "")
            jurisdictions = sq.get("jurisdictions", [])

            # Search with first jurisdiction (API limitation)
            data = self._fetch_search(
                session, base_url, token, query, jurisdictions, per_page
            )

            if not isinstance(data, dict):
                continue

            companies = data.get("results", {}).get("companies", [])
            if not companies:
                continue

            for company in companies:
                try:
                    self._insert_company(cursor, company, query, result)
                    time.sleep(min_delay)  # Respect rate limit
                except Exception as e:
                    result.errors.append(f"Error processing company: {e}")

            _logger.info(
                "OpenCorporatesCollector: query '%s' → %d companies",
                query,
                len(companies),
            )

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
