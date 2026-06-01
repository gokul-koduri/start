"""BLS BED (Business Employment Dynamics) collector for establishment survival rates.

Downloads Table 7 "Survival of private sector establishments by opening year"
from https://www.bls.gov/bdm/bdmage.htm as fixed-width text files.

BLS BED data is annual (not quarterly). Each row tracks a single birth cohort
and provides cumulative survival rates at 1, 2, 3, 5, ... years since birth.

Example file URL: https://www.bls.gov/bdm/us_age_naics_31_table7.txt
  (NAICS 31 = Manufacturing, aggregate of 31-33)
"""

import re
import sqlite3
import logging

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session
from db.dedup import dedup_bls_rate

_logger = logging.getLogger(__name__)

# Columns in the BLS BED Table 7 fixed-width format (approximate positions)
# The "Survival Rates Since Birth" column gives cumulative survival percentage
# at each year mark. For a cohort born in year Y:
#   - Row "March Y+1" → 1-year survival rate
#   - Row "March Y+2" → 2-year survival rate
#   - Row "March Y+3" → 3-year survival rate
#   - Row "March Y+5" → 5-year survival rate

BED_BASE_URL = "https://www.bls.gov/bdm"


class BLSSurvivalRateCollector(BaseCollector):
    """Fetches annual manufacturing survival rate data from BLS BED Table 7."""

    @property
    def name(self) -> str:
        return "bls_survival_rates"

    def collect(self, conn: sqlite3.Connection) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        bed_config = self.config.get("bls_bed", {})
        naics_codes = bed_config.get("naics_codes", [])

        if not naics_codes:
            result.errors.append("No BLS BED naics_codes configured")
            result.status = "failed"
            return result

        session = get_http_session()

        for naics_entry in naics_codes:
            naics_code = naics_entry.get("code", "")
            naics_label = naics_entry.get("label", naics_code)
            store_as = naics_entry.get("store_as", naics_code)  # e.g. "31-33"
            url = f"{BED_BASE_URL}/us_age_naics_{naics_code}_table7.txt"

            _logger.info("Fetching BLS BED Table 7: %s (%s) from %s", naics_label, naics_code, url)

            try:
                resp = session.get(url, timeout=60)
                resp.raise_for_status()
            except Exception as e:
                result.errors.append(f"Failed to fetch {url}: {e}")
                _logger.error("BLS BED download failed for %s: %s", naics_code, e)
                continue

            if "Sorry, the page you are looking for" in resp.text[:500]:
                result.errors.append(f"File not found: {url}")
                _logger.warning("BLS BED 404 for %s", url)
                continue

            cohorts = self._parse_table7(resp.text)
            _logger.info("Parsed %d cohorts from %s Table 7", len(cohorts), naics_label)

            inserted = self._insert_cohorts(conn, cohorts, store_as, naics_label, url, result)
            _logger.info("Inserted %d records for %s", inserted, naics_label)

        result.status = "partial" if result.errors else "success"
        return result

    def _parse_table7(self, text: str) -> list[dict]:
        """Parse BLS BED Table 7 fixed-width text into cohort data.

        Returns a list of dicts like:
            {
                "birth_year": 1994,
                "establishment_count": 26513,
                "survival_rates": {1: 82.8, 2: 71.4, 3: 64.3, 5: 53.0, ...}
            }
        """
        cohorts = []
        current_cohort = None

        for line in text.splitlines():
            # Detect cohort header: "Annual openings" followed by "Year ended: March YYYY"
            cohort_match = re.search(r"Year ended:\s+March\s+(\d{4})", line)
            if cohort_match:
                if current_cohort and current_cohort.get("survival_rates"):
                    cohorts.append(current_cohort)
                current_cohort = {
                    "birth_year": int(cohort_match.group(1)),
                    "establishment_count": None,
                    "survival_rates": {},
                }
                continue

            if current_cohort is None:
                continue

            # Parse data rows: "March YYYY  <count>  <emp>  <survival_rate>  ..."
            row_match = re.match(
                r"\s+March\s+(\d{4})\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)",
                line,
            )
            if not row_match:
                continue

            track_year = int(row_match.group(1))
            est_count = int(row_match.group(2).replace(",", ""))
            survival_pct = float(row_match.group(4))

            # First row of a cohort gives the initial establishment count
            if current_cohort["establishment_count"] is None:
                current_cohort["establishment_count"] = est_count

            # Calculate years since birth
            years_since = track_year - current_cohort["birth_year"]
            if years_since > 0:
                current_cohort["survival_rates"][years_since] = survival_pct

        # Don't forget the last cohort
        if current_cohort and current_cohort.get("survival_rates"):
            cohorts.append(current_cohort)

        return cohorts

    def _insert_cohorts(
        self,
        conn: sqlite3.Connection,
        cohorts: list[dict],
        naics_code: str,
        industry_name: str,
        source_url: str,
        result: CollectionResult,
    ) -> int:
        """Insert parsed cohort data into bls_survival_rates table.

        Each cohort becomes one row with 1yr/2yr/3yr/5yr survival columns populated.
        Returns the number of records inserted.
        """
        inserted = 0

        for cohort in cohorts:
            birth_year = cohort["birth_year"]
            est_count = cohort["establishment_count"]
            rates = cohort["survival_rates"]

            # Check dedup
            if dedup_bls_rate(conn, naics_code, birth_year):
                result.records_skipped += 1
                continue

            age_1 = rates.get(1)
            age_2 = rates.get(2)
            age_3 = rates.get(3)
            age_5 = rates.get(5)

            # Only insert if we have at least the 1-year survival rate
            if age_1 is None:
                result.records_skipped += 1
                continue

            conn.execute(
                """INSERT INTO bls_survival_rates
                   (naics_code, industry_name, year, quarter,
                    age_1_yr_survival, age_2_yr_survival, age_3_yr_survival, age_5_yr_survival,
                    establishment_count, source_url, collected_at)
                   VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (naics_code, industry_name, birth_year,
                 age_1, age_2, age_3, age_5,
                 est_count, source_url),
            )
            result.records_collected += 1
            result.records_inserted += 1
            inserted += 1

        conn.commit()
        return inserted

    def _get_max_year(self, conn: sqlite3.Connection) -> int | None:
        """Get the maximum birth year currently in the database."""
        row = conn.execute(
            "SELECT MAX(year) as max_year FROM bls_survival_rates"
        ).fetchone()
        if row and row["max_year"]:
            return int(row["max_year"])
        return None
