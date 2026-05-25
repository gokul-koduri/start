"""BLS Public API collector for manufacturing establishment survival rates."""

import sqlite3
import logging
import time

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session
from utils.rate_limiter import RateLimiter
from utils.date_parsing import parse_quarter
from db.dedup import dedup_bls_rate

_logger = logging.getLogger(__name__)


class BLSSurvivalRateCollector(BaseCollector):
    """Fetches quarterly manufacturing survival rate data from BLS Public API."""

    @property
    def name(self) -> str:
        return "bls_survival_rates"

    def collect(self, conn: sqlite3.Connection) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        bls_config = self.config.get("bls", {})
        api_config = self.config.get("api", {}).get("bls", {})
        base_url = api_config.get("base_url", "https://api.bls.gov/publicAPI/v2/timeseries/data/")
        api_key = api_config.get("api_key", "").strip()
        series_list = bls_config.get("series", [])
        start_year = bls_config.get("start_year", 2020)
        end_year = bls_config.get("end_year", 2025)

        if not series_list:
            result.errors.append("No BLS series configured")
            result.status = "failed"
            return result

        # Determine incremental start point
        last_year = self._get_max_year(conn)
        if last_year:
            start_year = max(start_year, last_year)
            _logger.info("Incremental: starting from year %d", start_year)

        # Determine batch size based on API key presence
        batch_size = 25 if not api_key else 50

        # Build series ID to metadata mapping
        series_map = {}
        for s in series_list:
            series_map[s["id"]] = s

        series_ids = list(series_map.keys())
        batches = [series_ids[i:i + batch_size] for i in range(0, len(series_ids), batch_size)]

        rate_limiter = RateLimiter(
            requests_per_minute=api_config.get("rate_limit", {}).get("requests_per_minute", 10)
        )
        session = get_http_session()

        for batch_idx, batch in enumerate(batches):
            rate_limiter.wait()

            payload = {
                "seriesid": batch,
                "startyear": str(start_year),
                "endyear": str(end_year),
                "registrationkey": api_key if api_key else None,
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            _logger.debug("BLS batch %d/%d: %d series from %d to %d",
                          batch_idx + 1, len(batches), len(batch), start_year, end_year)

            try:
                resp = session.post(base_url, json=payload, timeout=30)
                data = resp.json()
            except Exception as e:
                result.errors.append(f"BLS API request failed: {e}")
                _logger.error("BLS API error: %s", e)
                continue

            status = data.get("Results", {}).get("status", "")
            if status != "REQUEST_SUCCEEDED":
                result.errors.append(f"BLS returned status: {status}")
                _logger.warning("BLS status: %s", status)
                continue

            for series_data in data.get("Results", {}).get("series", []):
                series_id = series_data["seriesID"]
                meta = series_map.get(series_id, {})
                naics = meta.get("naics", "31-33")
                industry = meta.get("label", naics)
                metric = meta.get("metric", "")

                for point in series_data.get("data", []):
                    year = int(point["year"])
                    quarter = parse_quarter(point.get("period", ""))
                    value_str = point.get("value", "")

                    if quarter is None or not value_str or value_str == "-":
                        continue

                    try:
                        value = float(value_str)
                    except ValueError:
                        continue

                    # Check dedup
                    if dedup_bls_rate(conn, naics, year, quarter):
                        result.records_skipped += 1
                        continue

                    # Map metric to the right column
                    col_map = {
                        "births": None,
                        "deaths": None,
                        "survival_1yr": "age_1_yr_survival",
                        "survival_2yr": "age_2_yr_survival",
                        "survival_5yr": "age_5_yr_survival",
                    }
                    col_name = col_map.get(metric)

                    if col_name:
                        # Check if a row already exists for this naics/year/quarter
                        # and update the specific column, or insert
                        existing = conn.execute(
                            "SELECT id FROM bls_survival_rates WHERE naics_code = ? AND year = ? AND quarter = ?",
                            (naics, year, quarter),
                        ).fetchone()

                        if existing:
                            conn.execute(
                                f"UPDATE bls_survival_rates SET {col_name} = ? WHERE id = ?",
                                (value, existing["id"]),
                            )
                        else:
                            conn.execute(
                                """INSERT INTO bls_survival_rates
                                   (naics_code, industry_name, year, quarter, source_url, collected_at, """ + col_name + """)
                                   VALUES (?, ?, ?, ?, ?, datetime('now'), ?)""",
                                (naics, industry, year, quarter,
                                 f"https://api.bls.gov/publicAPI/v2/timeseries/data/{series_id}",
                                 value),
                            )
                        result.records_collected += 1
                        result.records_inserted += 1
                    else:
                        result.records_collected += 1
                        result.records_skipped += 1

                conn.commit()

        result.status = "partial" if result.errors else "success"
        return result

    def _get_max_year(self, conn: sqlite3.Connection) -> int | None:
        """Get the maximum year currently in the database for incremental collection."""
        row = conn.execute(
            "SELECT MAX(year) as max_year FROM bls_survival_rates"
        ).fetchone()
        if row and row["max_year"]:
            return int(row["max_year"])
        return None
