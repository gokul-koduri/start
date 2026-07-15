"""Pipeline Funding Intelligence Collector - tracks funding events and investment trends."""

import json
import logging
import time

from bs4 import BeautifulSoup
from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)


# Funding-related search terms
FUNDING_KEYWORDS = [
    "pipeline inspection funding",
    "pipeline monitoring startup funding",
    "pipeline robotics venture capital",
    "pipeline integrity funding",
    "pipeline AI startup funding",
    "leak detection startup funding",
    "pipeline digital twin investment",
]


class PipelineFundingCollector(BaseCollector):
    """Collects funding events for pipeline technology companies.

    Tracks:
    - Funding rounds (seed, series A, B, C, etc.)
    - Investor information
    - Acquisition events
    - Strategic partnerships

    Generates signals:
    - Rising technology areas
    - Investment velocity by category
    - Funding trends
    """

    @property
    def name(self) -> str:
        return "pipeline_funding"

    def collect(self, conn) -> CollectionResult:
        """Collect pipeline funding events from various sources."""
        result = CollectionResult(collector_name=self.name)
        session = get_http_session(user_agent="StartupResearchBot/1.0 (+funding)")

        config = self.config.get("collectors", {}).get("pipeline_funding", {})
        max_results = config.get("max_results", 20)
        delay_seconds = config.get("delay_seconds", 3)

        collected_companies = set()

        for keyword in FUNDING_KEYWORDS:
            search_url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&tbm=nws&num={max_results}"

            try:
                resp = session.get(search_url, timeout=15)
                if resp.status_code == 429:
                    result.errors.append(f"Rate limited on: {keyword}")
                    time.sleep(5)
                    continue
                if resp.status_code != 200:
                    continue
            except Exception as e:
                _logger.debug("Failed to fetch %s: %s", keyword, e)
                continue

            funding_events = self._parse_funding_news(resp.text, keyword)

            for event in funding_events:
                if self._insert_funding_event(conn, event):
                    result.records_inserted += 1
                result.records_collected += 1

                # Track company for pipeline company table
                if event["company_name"] not in collected_companies:
                    self._ensure_company_in_pipeline(conn, event)
                    collected_companies.add(event["company_name"])

            time.sleep(delay_seconds)

        return result

    def _parse_funding_news(self, html: str, keyword: str) -> list[dict]:
        """Parse funding news articles to extract funding details."""
        events = []
        soup = BeautifulSoup(html, "lxml")

        for item in soup.select("div.SoaBEf")[:15]:
            try:
                # Extract headline
                title_elem = item.select_one("div.MBeuO")
                title = title_elem.get_text(strip=True) if title_elem else ""

                # Extract source
                source_elem = item.select_one("div.CEMjEng span")
                source = source_elem.get_text(strip=True) if source_elem else "Unknown"

                # Extract date
                date_elem = item.select_one("div.OSrXXb span")
                date_str = date_elem.get_text(strip=True) if date_elem else ""

                # Extract description
                desc_elem = item.select_one("div.GI74Re")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                # Parse funding details from title and description
                funding_info = self._extract_funding_details(title, description)

                if funding_info["company_name"]:
                    funding_info.update({
                        "source": source,
                        "published_date": date_str,
                        "source_url": None,
                        "raw_title": title,
                    })
                    events.append(funding_info)

            except Exception as e:
                _logger.debug("Failed to parse funding event: %s", e)
                continue

        return events

    def _extract_funding_details(self, title: str, description: str) -> dict:
        """Extract funding details from article text."""
        text = f"{title} {description}"

        # Initialize result
        result = {
            "company_name": None,
            "round_type": None,
            "amount_usd": None,
            "investors": None,
            "valuation": None,
        }

        # Extract amount
        import re
        amounts = re.findall(r'\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B)?', text, re.IGNORECASE)
        if amounts:
            amount_val = float(amounts[0][0].replace(",", ""))
            unit = amounts[0][1].lower() if len(amounts[0]) > 1 else ""

            if unit in ["million", "m"]:
                amount_usd = int(amount_val * 1_000_000)
            elif unit in ["billion", "b"]:
                amount_usd = int(amount_val * 1_000_000_000)
            else:
                amount_usd = int(amount_val)

            result["amount_usd"] = amount_usd

        # Extract round type
        round_patterns = {
            "Seed": [r'\bseed\b', r'\bseed round\b', r'\bpre-seed\b'],
            "Series A": [r'\bseries\s*a\b', r'\bseries a\b'],
            "Series B": [r'\bseries\s*b\b', r'\bseries b\b'],
            "Series C": [r'\bseries\s*c\b', r'\bseries c\b'],
            "Acquisition": [r'\bacquired\b', r'\bAcquisition\b', r'\bbuys\b', r'\bpurchases\b'],
            "IPO": [r'\bIPO\b', r'\binitial public offering\b'],
        }

        for round_type, patterns in round_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    result["round_type"] = round_type
                    break
            if result["round_type"]:
                break

        # Extract company name (usually at the start of title)
        # Try to clean up common patterns
        name_match = re.match(r'^([A-Z][A-Za-z0-9\s&]+?)(?:\s*(?:raises|secures|wins|acquired|closes|announces))/i', title)
        if name_match:
            result["company_name"] = name_match.group(1).strip()
        else:
            # Fallback: first few words
            words = title.split()[:3]
            result["company_name"] = " ".join(words)

        # Extract investors
        investor_match = re.search(r'led by\s+([^,\.]+)', text, re.IGNORECASE)
        if investor_match:
            investors_text = investor_match.group(1).strip()
            result["investors"] = json.dumps([investors_text])

        # Extract valuation
        valuation_match = re.search(r'valuation (?:of\s+)?\$([0-9]+(?:\.[0-9]+)?)\s*(billion|million)?', text, re.IGNORECASE)
        if valuation_match:
            val = float(valuation_match.group(1).replace(",", ""))
            unit = valuation_match.group(2).lower() if valuation_match.group(2) else ""
            if unit == "billion":
                result["valuation"] = int(val * 1_000_000_000)
            else:
                result["valuation"] = int(val * 1_000_000)

        return result

    def _insert_funding_event(self, conn, event: dict) -> bool:
        """Insert funding event into database."""
        if not event.get("company_name"):
            return False

        cursor = conn.cursor()

        # Check for duplicate
        company = event["company_name"]
        round_type = event.get("round_type", "Unknown")
        announced = event.get("published_date", "")

        cursor.execute(
            """SELECT 1 FROM pipeline_funding_events
               WHERE company_name = %s AND round_type = %s LIMIT 1""",
            (company, round_type),
        )
        if cursor.fetchone():
            cursor.close()
            return False

        cursor.execute(
            """INSERT INTO pipeline_funding_events
               (company_name, round_type, amount_usd, announced_date,
                investors_json, valuation_at_round, source)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                company,
                round_type,
                event.get("amount_usd"),
                announced,
                event.get("investors"),
                event.get("valuation"),
                event.get("source", "google_news"),
            ),
        )
        cursor.close()
        return True

    def _ensure_company_in_pipeline(self, conn, event: dict) -> None:
        """Ensure company exists in pipeline_companies table."""
        if not event.get("company_name"):
            return

        cursor = conn.cursor()

        # Check if exists
        cursor.execute(
            "SELECT id FROM pipeline_companies WHERE name = %s LIMIT 1",
            (event["company_name"],),
        )
        existing = cursor.fetchone()

        if not existing:
            # Determine company type from round
            company_type = "active"
            if event.get("round_type") == "Acquisition":
                company_type = "acquired"

            # Estimate pipeline type from description
            pipeline_type = "management"
            raw_title = event.get("raw_title", "").lower()
            if any(t in raw_title for t in ["inspection", "pigging", "mfl"]):
                pipeline_type = "inspection"
            elif any(t in raw_title for t in ["leak", "monitor", "sensor"]):
                pipeline_type = "monitoring"
            elif any(t in raw_title for t in ["robot", "drone", "autonomous"]):
                pipeline_type = "infrastructure"

            cursor.execute(
                """INSERT INTO pipeline_companies
                   (name, pipeline_type, company_type, data_confidence_score)
                   VALUES (%s, %s, %s, %s)""",
                (event["company_name"], pipeline_type, company_type, 0.5),
            )

        cursor.close()


def get_funding_signals(conn) -> dict:
    """Generate investment signals from collected funding data."""
    cursor = conn.cursor()

    signals = {
        "rising_categories": [],
        "total_funding_2024": 0,
        "active_companies_funded": 0,
        "top_investors": [],
        "recent_rounds": [],
    }

    # Count funding by pipeline type
    cursor.execute("""
        SELECT pc.pipeline_type, COUNT(*) as cnt, SUM(pfe.amount_usd) as total
        FROM pipeline_funding_events pfe
        JOIN pipeline_companies pc ON pfe.company_name = pc.name
        GROUP BY pc.pipeline_type
        ORDER BY total DESC
    """)
    category_funding = cursor.fetchall()

    for row in category_funding:
        signals["rising_categories"].append({
            "category": row["pipeline_type"],
            "event_count": row["cnt"],
            "total_funding": row["total"] or 0,
        })

    # Total funding this year
    cursor.execute("""
        SELECT SUM(amount_usd) as total
        FROM pipeline_funding_events
        WHERE announced_date >= '2024-01-01'
    """)
    signals["total_funding_2024"] = cursor.fetchone()["total"] or 0

    # Active companies with recent funding
    cursor.execute("""
        SELECT COUNT(DISTINCT company_name) as cnt
        FROM pipeline_funding_events
        WHERE round_type != 'Acquisition'
    """)
    signals["active_companies_funded"] = cursor.fetchone()["cnt"]

    # Top investors
    cursor.execute("""
        SELECT investors_json, COUNT(*) as cnt
        FROM pipeline_funding_events
        WHERE investors_json IS NOT NULL
        GROUP BY investors_json
        ORDER BY cnt DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        if row["investors_json"]:
            investors = json.loads(row["investors_json"])
            for inv in investors:
                signals["top_investors"].append({
                    "name": inv,
                    "deals": row["cnt"],
                })

    # Recent rounds
    cursor.execute("""
        SELECT company_name, round_type, amount_usd, announced_date
        FROM pipeline_funding_events
        ORDER BY announced_date DESC
        LIMIT 10
    """)
    signals["recent_rounds"] = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    return signals


# CLI runner
if __name__ == "__main__":
    from config import setup_logging, load_config

    setup_logging()
    load_config()

    from db.connection import get_connection
    from db import schema

    conn = get_connection()
    schema.init_schema(conn)

    collector = PipelineFundingCollector()
    result = collector.collect(conn)

    print(f"Collected {result.records_collected} funding events")
    print(f"Inserted {result.records_inserted} new events")

    signals = get_funding_signals(conn)
    print("\nFunding Signals:")
    print(f"- Total funding 2024: ${signals['total_funding_2024']:,}")
    print(f"- Active companies funded: {signals['active_companies_funded']}")
    print(f"- Rising categories: {[c['category'] for c in signals['rising_categories'][:3]]}")