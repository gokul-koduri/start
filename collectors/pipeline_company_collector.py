"""Pipeline Company Collector - discovers and enriches pipeline industry companies."""

import logging
import time

from bs4 import BeautifulSoup

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)


# Pipeline technology categories for discovery
PIPELINE_CATEGORIES = {
    "inspection": [
        "pipeline inspection",
        "inline inspection",
        "mfl inspection",
        "ultrasonic testing pipeline",
        "pipeline pigging",
        "smart pig",
        "pipeline defect detection",
    ],
    "monitoring": [
        "pipeline monitoring",
        "pipeline leak detection",
        "fiber optic sensing pipeline",
        "pipeline acoustic monitoring",
        "pipeline pressure monitoring",
    ],
    "management": [
        "pipeline integrity management",
        "pipeline risk assessment",
        "corrosion management",
        "pipeline digital twin",
        "pipeline scada",
    ],
    "infrastructure": [
        "pipeline construction",
        "pipeline materials",
        "hdpe pipe",
        "composite pipe",
        "pipeline welding",
    ],
    "robotics": [
        "pipeline robot",
        "pipeline inspection robot",
        "autonomous pipeline",
        "pipeline drone",
    ],
    "hydrogen": [
        "hydrogen pipeline",
        "hydrogen transport",
        "hydrogen compatible pipe",
    ],
    "digital": [
        "pipeline software",
        "pipeline analytics",
        "pipeline AI",
        "pipeline data platform",
    ],
}


class PipelineCompanyCollector(BaseCollector):
    """Discovers and enriches pipeline industry companies.

    Sources:
    - Google search for company listings
    - Industry databases
    - Funding databases
    - Patent databases
    """

    @property
    def name(self) -> str:
        return "pipeline_company_collector"

    def collect(self, conn) -> CollectionResult:
        """Collect pipeline companies from various sources."""
        result = CollectionResult(collector_name=self.name)
        session = get_http_session(user_agent="StartupResearchBot/1.0 (+pipeline)")

        config = self.config.get("collectors", {}).get("pipeline_company_collector", {})
        max_companies_per_category = config.get("max_companies_per_category", 20)
        delay_seconds = config.get("delay_seconds", 2)

        all_discovered = []

        for category, search_terms in PIPELINE_CATEGORIES.items():
            _logger.info("Discovering companies in category: %s", category)

            for term in search_terms[:3]:  # Limit searches per category
                search_url = f"https://www.google.com/search?q={term.replace(' ', '+')}+company&num={max_companies_per_category}"

                try:
                    resp = session.get(search_url, timeout=15)
                    if resp.status_code == 429:
                        result.errors.append(f"Rate limited on: {term}")
                        time.sleep(5)
                        continue
                    if resp.status_code != 200:
                        continue
                except Exception as e:
                    _logger.debug("Failed to fetch %s: %s", term, e)
                    continue

                companies = self._parse_search_results(resp.text, category, term)
                all_discovered.extend(companies)

                time.sleep(delay_seconds)

        # Insert discovered companies
        for company in all_discovered:
            if self._insert_company(conn, company):
                result.records_inserted += 1
            result.records_collected += 1

        return result

    def _parse_search_results(self, html: str, category: str, search_term: str) -> list[dict]:
        """Parse Google search results to extract company information."""
        companies = []
        soup = BeautifulSoup(html, "lxml")

        # Look for company cards / knowledge panels
        for result in soup.select("div.g")[:10]:
            try:
                # Extract company name from title
                title_elem = result.select_one("h3")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Clean up company name (remove common suffixes)
                clean_name = self._clean_company_name(title)

                if len(clean_name) < 3:
                    continue

                # Extract description snippet
                snippet_elem = result.select_one("div.VwiC3b")
                description = snippet_elem.get_text(strip=True) if snippet_elem else ""

                # Extract website
                link = result.select_one("a")
                url = link.get("href", "") if link else ""

                # Determine pipeline type based on search
                pipeline_type = self._determine_pipeline_type(search_term)

                company = {
                    "name": clean_name,
                    "pipeline_type": pipeline_type,
                    "company_type": self._infer_company_type(description),
                    "description": description[:500] if description else None,
                    "source_url": url[:2048] if url else None,
                    "search_term": search_term,
                    "source": "google_search",
                    "data_confidence_score": 0.4,  # Lower confidence for scraped data
                }

                companies.append(company)

            except Exception as e:
                _logger.debug("Failed to parse result: %s", e)
                continue

        return companies

    def _clean_company_name(self, name: str) -> str:
        """Clean up company name from search results."""
        # Remove common suffixes
        suffixes = [
            " - Wikipedia",
            " | Official Website",
            " - Official Site",
            " - Crunchbase",
            " - LinkedIn",
            " Corporation",
            " Inc.",
            " LLC",
            " Ltd.",
            " GmbH",
        ]

        cleaned = name
        for suffix in suffixes:
            if suffix in cleaned:
                cleaned = cleaned.replace(suffix, "")

        return cleaned.strip()

    def _determine_pipeline_type(self, search_term: str) -> str:
        """Map search term to pipeline type."""
        type_mapping = {
            "inspection": ["inspection", "inline", "mfl", "ultrasonic", "pigging", "smart pig", "defect"],
            "monitoring": ["monitoring", "leak", "fiber optic", "acoustic", "pressure"],
            "management": ["integrity", "risk", "corrosion", "digital twin", "scada"],
            "infrastructure": ["construction", "materials", "pipe", "welding"],
            "robotics": ["robot", "autonomous", "drone"],
            "hydrogen": ["hydrogen"],
            "digital": ["software", "analytics", "AI", "data platform"],
        }

        for ptype, keywords in type_mapping.items():
            for keyword in keywords:
                if keyword.lower() in search_term.lower():
                    return ptype

        return "management"

    def _infer_company_type(self, description: str) -> str:
        """Infer company status from description."""
        desc_lower = description.lower()

        failed_terms = ["shutdown", "bankrupt", "defunct", "closed", "acquired"]
        active_terms = ["leading", "global", "innovative", "provider", "specialist", "offering"]

        for term in failed_terms:
            if term in desc_lower:
                return "failed"

        for term in active_terms:
            if term in desc_lower:
                return "active"

        return "active"  # Default to active

    def _insert_company(self, conn, company: dict) -> bool:
        """Insert or update company in database."""
        cursor = conn.cursor()

        # Check for duplicate
        cursor.execute(
            "SELECT id FROM pipeline_companies WHERE name = %s LIMIT 1",
            (company["name"],),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.close()
            return False

        cursor.execute(
            """INSERT INTO pipeline_companies
               (name, pipeline_type, company_type, description, source_url,
                source, data_confidence_score)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                company["name"],
                company["pipeline_type"],
                company["company_type"],
                company.get("description"),
                company.get("source_url"),
                company.get("source", "google_search"),
                company.get("data_confidence_score", 0.5),
            ),
        )
        cursor.close()
        return True

    def enrich_company(self, conn, company_name: str, enrichment_data: dict) -> bool:
        """Enrich existing company with additional data."""
        cursor = conn.cursor()

        update_fields = []
        values = []

        for field, value in enrichment_data.items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                values.append(value)

        if not update_fields:
            cursor.close()
            return False

        update_fields.append("last_enriched_at = NOW()")
        values.append(company_name)

        cursor.execute(
            f"""UPDATE pipeline_companies
                SET {', '.join(update_fields)}
                WHERE name = %s""",
            values,
        )

        affected = cursor.rowcount
        conn.commit()
        cursor.close()

        return affected > 0


# CLI runner
if __name__ == "__main__":
    from config import setup_logging, load_config

    setup_logging()
    load_config()

    from db.connection import get_connection
    from db import schema

    conn = get_connection()
    schema.init_schema(conn)

    collector = PipelineCompanyCollector()
    result = collector.collect(conn)

    print(f"Discovered {result.records_collected} companies")
    print(f"Inserted {result.records_inserted} new companies")
    print(f"Skipped {result.records_skipped} duplicates")
    if result.errors:
        print(f"Errors: {result.errors[:3]}")