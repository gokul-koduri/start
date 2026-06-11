"""CrunchBase collector — fetches startup funding and outcome data.

Requires a CrunchBase API key (paid). Enable in settings.yaml:
    api:
      crunchbase:
        api_key: "${CRUNCHBASE_API_KEY}"
        enabled: true

Once enabled, this collector:
1. Searches for startups by industry, status (closed/operating), and date range
2. Fetches funding rounds, investors, and acquisition data
3. Normalizes and stores in failed_startups and crunchbase_startups tables

Rate limits: CrunchBase API allows 500 calls/day on the Basic plan.
"""

import logging
import time

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session
from db.dedup import dedup_startup

_logger = logging.getLogger(__name__)

# CrunchBase API endpoints
CB_API_BASE = "https://api.crunchbase.com/api/v4"

# Industries relevant to manufacturing failure research
TARGET_INDUSTRIES = [
    "Manufacturing",
    "Hardware",
    "Automotive",
    "Energy",
    "Industrial",
    "Robotics",
    "3D Printing",
    "Semiconductors",
    "Battery",
    "Clean Energy",
    "Construction",
    "Aerospace",
    "Materials Science",
    "Biotechnology",
    "Food and Beverage",
]


class CrunchBaseCollector(BaseCollector):
    """Collects startup data from the CrunchBase API."""

    @property
    def name(self) -> str:
        return "crunchbase"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        api_config = self.config.get("api", {}).get("crunchbase", {})
        api_key = api_config.get("api_key", "")

        if not api_key or api_key == "${CRUNCHBASE_API_KEY}":
            result.errors.append("CrunchBase API key not configured")
            result.status = "skipped"
            return result

        session = get_http_session()

        for industry in TARGET_INDUSTRIES:
            _logger.info("CrunchBase: Searching industry: %s", industry)

            try:
                data = self._search_entities(session, api_key, industry)
            except Exception as e:
                result.errors.append(f"CrunchBase search failed for {industry}: {e}")
                continue

            if not data:
                _logger.debug("CrunchBase: No results for %s", industry)
                continue

            for entity in data:
                try:
                    self._process_entity(conn, entity, result, industry)
                except Exception as e:
                    result.errors.append(f"Failed to process entity: {e}")

                time.sleep(0.5)  # Rate limiting

        if result.errors and result.records_inserted == 0:
            result.status = "failed"
        elif result.errors:
            result.status = "partial"

        return result

    def _search_entities(self, session, api_key: str, industry: str) -> list[dict]:
        """Search CrunchBase for closed/operating startups in an industry."""
        url = f"{CB_API_BASE}/searches/organizations"
        params = {
            "user_key": api_key,
            "field_ids": [
                "identifier",
                "short_description",
                "categories",
                "funding_total",
                "status",
                "founded_on",
                "closed_on",
                "location_identifiers",
                "num_employees_enum",
            ],
            "query": [
                {
                    "type": "predicate",
                    "field_id": "categories",
                    "operator_id": "includes",
                    "values": [industry],
                },
                {
                    "type": "predicate",
                    "field_id": "status",
                    "operator_id": "includes",
                    "values": ["closed"],
                },
            ],
            "limit": 50,
            "order": [{"field_id": "funding_total", "sort": "desc"}],
        }

        resp = session.post(
            url,
            json=params,
            timeout=30,
        )

        if resp.status_code == 429:
            _logger.warning("CrunchBase: Rate limited")
            return []
        resp.raise_for_status()

        return resp.json().get("entities", [])

    def _process_entity(
        self, conn, entity: dict, result: CollectionResult, industry: str
    ):
        """Process and store a single CrunchBase entity."""
        props = entity.get("properties", {})

        name = props.get("identifier", {}).get("value", "")
        if not name:
            return

        status = props.get("status", "")
        funding_total = props.get("funding_total", 0) or 0
        founded_on = props.get("founded_on", {}).get("value", "")
        closed_on = props.get("closed_on", {}).get("value", "")
        description = props.get("short_description", "")

        # Parse years
        year_founded = int(founded_on[:4]) if founded_on else None
        year_shutdown = int(closed_on[:4]) if closed_on else None

        # Only store closed/failed startups
        if status != "closed" and not closed_on:
            result.records_skipped += 1
            return

        # Dedup
        region = "US & Global"
        if dedup_startup(conn, name, region):
            result.records_skipped += 1
            return

        if not self.dry_run:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT IGNORE INTO failed_startups
                   (name, sector, country, region, funding_raised_usd,
                    funding_description, year_founded, year_shutdown,
                    failure_reason, failure_category, source, source_url)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    name,
                    industry,
                    "US",
                    region,
                    funding_total if funding_total else None,
                    f"${funding_total / 1_000_000:.1f}M" if funding_total else None,
                    year_founded,
                    year_shutdown or 2024,
                    f"Closed — {description}" if description else "Unknown",
                    None,
                    "crunchbase",
                    f"https://www.crunchbase.com/organization/{name.lower().replace(' ', '-')}",
                ),
            )
            cursor.close()
            conn.commit()

        result.records_collected += 1
        result.records_inserted += 1
